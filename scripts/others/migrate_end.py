import xmlrpc.client
import mysql.connector
import sys

print("==================================================")
print("🚀 INICIANDO MIGRACIÓN AUTOMATIZADA: MYSQL -> ODOO")
print("==================================================")

# 1. CREDENCIALES COMPROBADAS
ODOO_URL = 'http://localhost:8069'
ODOO_DB = 'odoo_portfolio'          
ODOO_USER = 'gmunoz1151@gmail.com'  # 👈 Pon tu correo real aquí
ODOO_PASS = 'CLOUDodoo26#'    # 👈 Pon tu contraseña real aquí

MYSQL_CONFIG = {
    'host': 'localhost',             
    'user': 'bashtico',
    'password': 'PATsistemas26#', # 👈 Pon tu contraseña de MySQL aquí
    'database': 'db_almacen' # 👈 Pon el nombre de tu base aquí
}

# Diccionarios de homologación (Mapeos)
MAPEO_UNIDADES = {'pza': 1, 'mtr': 12, 'mtc': 19, 'kgr': 3, 'lts': 10, 'mt2': 25, 'blt': 1, 'par': 1}

MAPEO_CUENTAS_CATEGORIAS = {
    "2.4.1.1": "Productos Minerales no Metálicos",
    "2.4.2.1": "Cemento y Productos de Concreto",
    "2.4.3.1": "Cal, Yeso y Productos de Yeso",
    "2.4.4.1": "Madera y Productos de Madera",
    "2.4.6.1": "Material Eléctrico y Eléctronico",
    "2.4.7.1": "Artículos Métalicos para la Construccción",
    "2.4.9.1": "Otros Materiales y Artículos de Construcción  Y Reparación",
    "2.5.6.1": "Fibras Sintéticas, Hules, Plásticos Y Derivados",
    "2.7.2.1": "Prendas de Seguridad Y Protección Personal",
    "2.9.1.1": "Herramientas menores",
    "2.9.2.1": "Refacciones y Accesorios Menores de Edificios",
    "5.6.7.1": "Herramientas Y Máquinas-Herramienta"
    
}


# --- Conexión a Odoo via API ---
try:
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
    if not uid:
        print("❌ Error: Credenciales de Odoo incorrectas.")
        sys.exit()
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    print(f"✅ Odoo conectado con éxito (UID: {uid})")
except Exception as e:
    print(f"❌ Fallo al conectar con Odoo: {e}")
    sys.exit()

def obtener_o_crear_categoria_automatizada(codigo_cuenta):
    """Busca la categoría por nombre. Si no existe, la crea enlazándola a la cuenta de Odoo."""
    cuenta_limpia = str(codigo_cuenta).strip()
    nombre_cat = MAPEO_CUENTAS_CATEGORIAS.get(cuenta_limpia)
    
    if not nombre_cat:
        # Si la cuenta es de consumibles (ej: herramientas), la mandamos a una sección de gasto manual
        return 1  # Por defecto 'All'
        
    # Verificar si la categoría ya existe
    cat_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'product.category', 'search', [[['name', '=', nombre_cat]]])
    if cat_ids:
        return cat_ids[0]
        
    print(f"   📁 Creando categoría contable en Odoo: {nombre_cat}...")
    
    # Buscamos el ID dinámico de la cuenta en Odoo (como la prueba exitosa que hicimos)
    account_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'account.account', 'search', [[['code', 'like', cuenta_limpia]]])
    
    payload_categoria = {
        'name': nombre_cat,
        'parent_id': 3,  # ID correspondiente a 'all / saleable'
        'property_cost_method': 'standard',
        'property_valuation': 'real_time', # Forzamos valoración automatizada en la DB
    }
    
    if account_ids:
        payload_categoria['property_stock_valuation_account_id'] = account_ids[0]
        print(f"      -> Cuenta contable enlazada (Odoo ID: {account_ids[0]})")
    else:
        print(f"      ⚠️ Advertencia: No se encontró la cuenta {cuenta_limpia} en Odoo. Valoración en Manual.")
        payload_categoria['property_valuation'] = 'manual_selection'

    return models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'product.category', 'create', [payload_categoria])

# --- Conexión a tu MySQL ---
try:
    db_mysql = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = db_mysql.cursor(dictionary=True)
    
    # ⚠️ REEMPLAZA CON EL NOMBRE REAL DE TU TABLA Y SUS COLUMNAS EN MYSQL
    query = "select codigo,nombre,precio,costo,unidad,ccontable from articulo"
    cursor.execute(query)
    productos_legacy = cursor.fetchall()
    print(f"✅ Conectado a MySQL. {len(productos_legacy)} artículos listos para migrar.")
except mysql.connector.Error as err:
    print(f"❌ Error en MySQL: {err}")
    sys.exit()

# --- Proceso ETL Masivo ---
print("\n⚙️ Procesando inserciones...")
for item in productos_legacy:
    unidad_key = str(item['unidad']).lower().strip()
    uom_id = MAPEO_UNIDADES.get(unidad_key, 1)
    
    # Llamamos a nuestra función blindada
    categ_id = obtener_o_crear_categoria_automatizada(item['ccontable'])
    
    payload_producto = {
        'name': item['nombre'],
        'default_code': item['codigo'],
        'list_price': float(item['precio']),
        'standard_price': float(item['costo']),
        'detailed_type': 'product',  # Producto almacenable
        'uom_id': uom_id,
        'uom_po_id': uom_id,
        'categ_id': categ_id
    }
    
    try:
        prod_id = models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'product.template', 'create', [payload_producto])
        print(f"   -> [✓ MIGRADO] {item['nombre']} -> Odoo ID: {prod_id}")
    except Exception as e:
        print(f"   -> [✗ ERROR] No se pudo migrar {item['nombre']}: {e}")

# Cerrar flujos de datos
cursor.close()
db_mysql.close()
print("\n==================================================")
print("🎉 ¡PROCESO FINALIZADO CON ÉXITO EN TU PORTAFOLIO!")
print("==================================================")
