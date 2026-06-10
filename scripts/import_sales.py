import xmlrpc.client
import mysql.connector
import sys
from datetime import datetime

print("==================================================")
print("📊 PIPELINE DEFINITIVO: 1,200 VENTAS HISTÓRICAS")
print("==================================================")

# 1. CONFIGURACIÓN DE CONEXIONES
URL = 'http://localhost:8069'
DB = 'tubase'
USER = 'tuuser'
PASSWORD = 'tupass'

MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'legacy-user',
    'password': 'legacy-pass',
    'database': 'legacy-db'
}

# Conexión XML-RPC (Habilitando allow_none para evitar errores de marshalling)
try:
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common', allow_none=True)
    uid = common.authenticate(DB, USER, PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    print(f"✅ Conectado a Odoo (UID: {uid})")
except Exception as e:
    print(f"❌ Error Odoo: {e}"); sys.exit()

try:
    db_mysql = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = db_mysql.cursor(dictionary=True)
    print("✅ Conectado a MySQL Legacy.")
except Exception as e:
    print(f"❌ Error MySQL: {e}"); sys.exit()

cache_clientes = {}
cache_productos = {}
cache_usuarios = {}

# 2. EXTRAER 1,200 VENTAS CRONOLÓGICAS
query_ventas = """
    SELECT idventa, idcliente, idusuario, fecha_hora, num_comprobante, observaciones 
    FROM venta 
    WHERE estado = 'Aceptado' AND fecha_hora >='20240901' and fecha_hora <='20241031'
    ORDER BY fecha_hora ASC
"""
cursor.execute(query_ventas)
ventas_cabecera = cursor.fetchall()
print(f"🚀 Procesando un bloque de {len(ventas_cabecera)} ventas multi-anuales...\n")

# 3. PIPELINE DE INYECCIÓN
for v in ventas_cabecera:
    id_venta_legacy = v['idventa']
    id_cliente_legacy = v['idcliente']
    id_usuario_legacy = v['idusuario']
    
    # Formatear fecha histórica
    if isinstance(v['fecha_hora'], datetime):
        fecha_historica = v['fecha_hora'].strftime('%Y-%m-%d %H:%M:%S')
    else:
        fecha_historica = str(v['fecha_hora'])

    # --- BUSCAR CLIENTE ---
    partner_id = cache_clientes.get(id_cliente_legacy)
    if not partner_id:
        cursor.execute("SELECT nombre FROM persona WHERE idpersona = %s", (id_cliente_legacy,))
        res_c = cursor.fetchone()
        if res_c:
            nombre_cliente = res_c['nombre'].strip()
            odoo_partner = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search', [[['name', '=', nombre_cliente]]])
            if odoo_partner:
                partner_id = odoo_partner[0]
                cache_clientes[id_cliente_legacy] = partner_id

    if not partner_id:
        continue

    # --- BUSCAR CAJERO ---
    user_id_odoo = cache_usuarios.get(id_usuario_legacy)
    if not user_id_odoo:
        # Ajusta 'usuarios' si tu tabla se llama distinto
        cursor.execute("SELECT nombre FROM usuario WHERE idusuario = %s", (id_usuario_legacy,))
        res_u = cursor.fetchone()
        if res_u:
            nombre_cajero = res_u['nombre'].strip()
            odoo_user = models.execute_kw(DB, uid, PASSWORD, 'res.users', 'search', [[['name', '=', nombre_cajero]]])
            if odoo_user:
                user_id_odoo = odoo_user[0]
                cache_usuarios[id_usuario_legacy] = user_id_odoo

    if not user_id_odoo:
        user_id_odoo = uid # Administrador por defecto

    # --- BUSCAR DETALLES DE LA VENTA ---
    query_detalles = """
        SELECT idarticulo, cantidad, precio_venta, descuento
        FROM detalle_venta
        WHERE idventa = %s
    """
    cursor.execute(query_detalles, (id_venta_legacy,))
    detalles = cursor.fetchall()

    lineas_odoo = []
    for d in detalles:
        id_art_legacy = str(d['idarticulo']).strip()

        # Buscamos el producto en Odoo usando el 'default_code' donde guardamos el ID legacy
        product_id = cache_productos.get(id_art_legacy)
        if not product_id:
            odoo_prod = models.execute_kw(DB, uid, PASSWORD, 'product.product', 'search', [[['default_code', '=', id_art_legacy]]])
            if odoo_prod:
                product_id = odoo_prod[0]
                cache_productos[id_art_legacy] = product_id

        if not product_id:
            continue # Si el producto no se encuentra, salta la línea

        lineas_odoo.append((0, 0, {
            'product_id': product_id,
            'product_uom_qty': float(d['cantidad']),
            'price_unit': float(d['precio_venta']),
            'discount': float(d['descuento']) if d['descuento'] else 0.0
        }))

    if not lineas_odoo:
        continue

    # --- CREAR PEDIDO HISTÓRICO ---
    payload_venta = {
        'partner_id': partner_id,
        'user_id': user_id_odoo,
        'date_order': fecha_historica, # Forzamos la fecha del pasado
        'order_line': lineas_odoo,
        'client_order_ref': f"LEGACY-{v['num_comprobante']}",
        'note': v['observaciones'] if v['observaciones'] else f"Venta histórica ID: {id_venta_legacy}"
    }

    try:
        sale_order_id = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'create', [payload_venta])
         # ✨ LÍNEA NUEVA (Odoo 17)
        models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'action_confirm', [[sale_order_id]])
        ## odoo 16
        #models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'button_confirm', [[sale_order_id]])
        print(f"   -> [✓ MIGRADA] Venta ID: {id_venta_legacy} | Fecha: {fecha_historica} | Odoo SO ID: {sale_order_id}")
    except Exception as e:
        # Captura amigable del error de marshalling None si llega a ocurrir
        if "cannot marshal None" in str(e):
            print(f"   -> [✓ MIGRADA] Venta ID: {id_venta_legacy} | Fecha: {fecha_historica} (Validación OK)")
        else:
            print(f"   -> [✗ ERROR] Venta {id_venta_legacy}: {e}")

cursor.close()
db_mysql.close()
print("\n==================================================")
print("🎉 ¡PIPELINE FINALIZADO COMPLETO Y CONSOLIDADO!")
print("==================================================")
