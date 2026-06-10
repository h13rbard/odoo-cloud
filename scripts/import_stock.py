
import xmlrpc.client
import mysql.connector
import sys

print("==================================================")
print("📦 PIPELINE: IMPORTACIÓN DE PRODUCTOS (CON COSTOS)")
print("==================================================")

# 1. CONFIGURACIÓN DE CONEXIONES
URL = 'http://localhost:8069'
DB = 'tudb'          
USER = 'tuuser'   
PASSWORD = 'tupass' 

MYSQL_CONFIG = {
    'host': 'localhost',             
    'user': 'legacy-user',
    'password': 'legacy-pass', 
    'database': 'legacy-db' 
}

# Conexión XML-RPC con Odoo
try:
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    print(f"✅ Conectado a Odoo exitosamente (UID: {uid})")
except Exception as e:
    print(f"❌ Error al conectar con Odoo: {e}"); sys.exit()

# Conexión con MySQL Legacy
try:
    db_mysql = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = db_mysql.cursor(dictionary=True)
    print("✅ Conectado a MySQL Legacy.")
except Exception as e:
    print(f"❌ Error al conectar con MySQL: {e}"); sys.exit()

# 2. LEER CATÁLOGO COMPLETO INCLUYENDO COSTO
# ⚠️ REVISA: Si en tu MySQL el campo no se llama 'precio_compra', cámbialo aquí abajo (ej. por 'costo')
query_productos = """
    SELECT idarticulo, nombre, precio_compra, precio_venta, stock 
    FROM articulo
"""
cursor.execute(query_productos)
productos_legacy = cursor.fetchall()
print(f"📊 MySQL leído. {len(productos_legacy)} productos listos para procesar.\n")

print("⚙️ Iniciando migración a tablas de Odoo...")

# 3. ITERACIÓN MIGRATORIA INTEGRA
for prod in productos_legacy:
    codigo_legacy = str(prod['idarticulo']).strip() 
    nombre_producto = " ".join(prod['nombre'].split()).strip() 
    
    # Valores numéricos seguros
    precio_venta = float(prod['precio_venta']) if prod['precio_venta'] else 0.0
    precio_costo = float(prod['precio_compra']) if prod['precio_compra'] else 0.0 # 👈 Agregado de seguridad
    stock_inicial = float(prod['stock']) if prod['stock'] else 0.0

    # --- PASO A: BUSCAR SI EL PRODUCTO YA EXISTE EN ODOO ---
    product_ids = models.execute_kw(DB, uid, PASSWORD, 'product.product', 'search', [[['default_code', '=', codigo_legacy]]])
    
    if not product_ids:
        # ✨ CREACIÓN DE RAÍZ INYECTANDO PRECIO Y COSTO FINANCIERO ✨
        payload_crear = {
            'name': nombre_producto,
            'default_code': codigo_legacy,  
            'list_price': precio_venta,       # Precio al público
            'standard_price': precio_costo,   # 👈 COSTO DE COMPRA (Mapeo financiero Odoo)
            'detailed_type': 'product',     
        }
        try:
            product_id = models.execute_kw(DB, uid, PASSWORD, 'product.product', 'create', [payload_crear])
            print(f"   -> [✓ CREADO] '{nombre_producto}' | Venta: ${precio_venta} | Costo: ${precio_costo}")
        except Exception as e:
            print(f"   ❌ Error crítico al crear '{nombre_producto}': {e}")
            continue
    else:
        product_id = product_ids[0]
        print(f"   ⚠️ Saltado: '{nombre_producto}' ya existe en Odoo.")

    # --- PASO B: INYECTAR EL STOCK INICIAL ---
    if stock_inicial > 0:
        try:
            quant_data = {
                'product_id': product_id,
                'location_id': 8, 
                'inventory_quantity': stock_inicial,
            }
            quant_id = models.execute_kw(DB, uid, PASSWORD, 'stock.quant', 'create', [quant_data])
            models.execute_kw(DB, uid, PASSWORD, 'stock.quant', 'action_apply_inventory', [[quant_id]])
            print(f"      📦 Stock inyectado con éxito: {stock_inicial} unidades.")
        except Exception as e:
            print(f"      ❌ Error al aplicar inventario para el Producto ID {product_id}: {e}")

cursor.close()
db_mysql.close()
print("\n==================================================")
print("🎉 ¡PROCESO FINALIZADO: CATÁLOGO CON MARGENES OK!")
print("==================================================")
