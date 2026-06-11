import xmlrpc.client
import mysql.connector
import sys

print("==================================================")
print("👥 MIGRACIÓN MAESTRA DE CONTACTOS Y PERSONAL A ODOO")
print("==================================================")

# 1. CONFIGURACIÓN DE CONEXIONES (Actualiza con tus datos reales)
URL = 'http://localhost:8069'
DB = 'tubase'          
USER = 'tuuser'   # 👈 Tu correo de Odoo
PASSWORD = 'tupass' # 👈 Tu contraseña de Odoo

MYSQL_CONFIG = {
    'host': 'localhost',             
    'user': 'legacy-user',
    'password': 'legacy-pass', # 👈 Tu contraseña de MySQL
    'database': 'legacy-db' # 👈 El nombre de tu base legacy montada
}

# Conexión con Odoo vía XML-RPC
try:
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    print(f"✅ Conectado a Odoo exitosamente (UID: {uid})")
except Exception as e:
    print(f"❌ Error al conectar a Odoo: {e}"); sys.exit()

# 2. CREAR O BUSCAR LA ETIQUETA "Personal Operativo" EN ODOO
try:
    tag_ids = models.execute_kw(DB, uid, PASSWORD, 'res.partner.category', 'search', [[['name', '=', 'Personal Operativo']]])
    if not tag_ids:
        TAG_OPERATIVO_ID = models.execute_kw(DB, uid, PASSWORD, 'res.partner.category', 'create', [{'name': 'Personal Operativo'}])
    else:
        TAG_OPERATIVO_ID = tag_ids[0]
    print("✅ Etiqueta 'Personal Operativo' verificada.")
except Exception as e:
    print(f"⚠️ Alerta con las etiquetas: {e}")
    TAG_OPERATIVO_ID = False

# 3. EXTRAER DATOS ACTUALIZADOS DE MYSQL
try:
    db_mysql = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = db_mysql.cursor(dictionary=True)
    
    # Consulta exacta basada en tu tabla 'persona'
    query = """
        SELECT tipo_persona, nombre, num_documento, direccion, telefono, email 
        FROM persona
    """
    cursor.execute(query)
    personas_legacy = cursor.fetchall()
    print(f"✅ MySQL leído. {len(personas_legacy)} registros listos para migrar.")
except mysql.connector.Error as err:
    print(f"❌ Error al leer MySQL: {err}"); sys.exit()

# 4. PROCESAR E INYECTAR EN ODOO
print("\n⚙️ Iniciando inserción en el modelo res.partner...")
    # ------------------------------------------
for per in personas_legacy:
    if not per['nombre']:
        continue
        
    # 1. Sanitizar Nombre (Eliminar espacios extras y saltos de línea)
    nombre_contacto = " ".join(per['nombre'].split()).strip()
    tipo = str(per['tipo_persona']).strip().lower()
    
    # 2. Sanitizar RFC (Evitar meter "MX" a textos como "N/A", "0", o vacíos)
    rfc_legacy = str(per['num_documento']).strip().replace("-", "").replace(" ", "") if per['num_documento'] else ""
    rfc_odoo = False
    
    # Solo procesamos como RFC si tiene una longitud lógica (11 a 13 caracteres alfanuméricos)
    if rfc_legacy and len(rfc_legacy) >= 10 and rfc_legacy.isalnum():
        if rfc_legacy.upper().startswith('MX'):
            rfc_odoo = rfc_legacy.upper()
        else:
            rfc_odoo = f"MX{rfc_legacy.upper()}"
            
    # 3. Sanitizar Dirección, Teléfono y Email (Limpiar nulos y saltos de línea)
    direccion_odoo = " ".join(str(per['direccion']).split()).strip() if per['direccion'] else False
    telefono_odoo = str(per['telefono']).strip().replace(" ", "") if per['telefono'] else False
    email_odoo = str(per['email']).strip().lower() if per['email'] else False

    # Mapeo de roles
    es_cliente = 1 if tipo == 'cliente' else 0
    es_proveedor = 1 if tipo == 'proveedor' else 0
    
    # Payload ultra-sanitizado
    payload_partner = {
        'name': nombre_contacto,
        'vat': rfc_odoo,
        'street': direccion_odoo,
        'phone': telefono_odoo,
        'email': email_odoo,
        'customer_rank': es_cliente,
        'supplier_rank': es_proveedor,
        'company_type': 'company' 
    }
    
    if tipo == 'operativo' and TAG_OPERATIVO_ID:
        payload_partner['category_id'] = [[6, 0, [TAG_OPERATIVO_ID]]]
        tipo_str = "OPERATIVO"
    elif es_cliente:
        tipo_str = "CLIENTE"
    elif es_proveedor:
        tipo_str = "PROVEEDOR"
    else:
        tipo_str = tipo.upper()

    try:
        # Verificar duplicados
        existe = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search', [[['name', '=', nombre_contacto]]])
        if existe:
            print(f"   ⚠️ Saltado: '{nombre_contacto}' ya existe.")
            continue
            
        # Crear registro
        partner_id = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'create', [payload_partner])
        print(f"   -> [✓ MIGRADO] ({tipo_str}) {nombre_contacto} -> ID Odoo: {partner_id}")
        
    except Exception as e:
        print(f"   -> [✗ ERROR] No se pudo migrar a {nombre_contacto}: {e}")
  # Cierre seguro de conexiones
cursor.close()
db_mysql.close()
print("\n==================================================")
print("🎉 ¡PROCESO DE MIGRACIÓN DE CONTACTOS FINALIZADO!")
print("==================================================")
