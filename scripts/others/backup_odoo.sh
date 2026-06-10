#!/bin/bash

# =====================================================================
# 💾 SCRIPT DE RESPALDO AUTOMÁTICO - LOCAL COMPROBADO
# =====================================================================

# 1. CONFIGURACIÓN EXACTA DE TUS CONTENEDORES
RESPALDO_DIR="/home/vagrant/odoo-cloud/backups"
FECHA=$(date +%Y-%m-%d_%H-%M-%S)
LOG_FILE="$RESPALDO_DIR/backup_log.txt"

CONTAINER_DB="odoo_db_local"   # 💡 Actualizado
CONTAINER_WEB="odoo_web_local" # 💡 Actualizado
DB_NAME="odoo_portfolio"
DB_USER="odoo"

mkdir -p "$RESPALDO_DIR"

echo "==================================================" | tee -a "$LOG_FILE"
echo "🕒 [$FECHA] Iniciando respaldo de Odoo..." | tee -a "$LOG_FILE"
echo "==================================================" | tee -a "$LOG_FILE"

# 2. RESPALDO DE LA BASE DE DATOS (PostgreSQL)
echo "📦 1/3. Extrayendo base de datos desde PostgreSQL..." | tee -a "$LOG_FILE"
docker exec -t $CONTAINER_DB pg_dump -U $DB_USER -F c -b -v -f /tmp/db_dump_$FECHA.sql $DB_NAME

# Copiar el archivo dump desde el contenedor al host
docker cp $CONTAINER_DB:/tmp/db_dump_$FECHA.sql $RESPALDO_DIR/odoo_db_$FECHA.sql
docker exec -t $CONTAINER_DB rm /tmp/db_dump_$FECHA.sql

if [ -f "$RESPALDO_DIR/odoo_db_$FECHA.sql" ]; then
  echo "   -> [✓ DB] Base de datos extraída correctamente." | tee -a "$LOG_FILE"
else
  echo "   -> [✗ ERROR] Falló la extracción de la Base de Datos." | tee -a "$LOG_FILE"
fi

# 3. RESPALDO DE FILESTORE (Búsqueda dinámica del directorio de datos)
echo "📁 2/3. Respaldando carpetas físicas (Filestore)..." | tee -a "$LOG_FILE"

# 💡 TRUCO: Le preguntamos a Odoo dentro del contenedor cuál es su ruta de filestore real
RUTA_INTERNA_FILESTORE=$(docker exec -t $CONTAINER_WEB find /var/lib/odoo -name filestore 2>/dev/null | tr -d '\r' | head -n 1)

# Si la ruta anterior regresa vacía por permisos, usamos la ruta base por defecto de la imagen oficial
if [ -z "$RUTA_INTERNA_FILESTORE" ]; then
  RUTA_INTERNA_FILESTORE="/var/lib/odoo/filestore"
fi

echo "   -> Ruta detectada en contenedor: $RUTA_INTERNA_FILESTORE" | tee -a "$LOG_FILE"

# Comprimimos directamente apuntando a la ruta encontrada
docker exec -t $CONTAINER_WEB tar -czf /tmp/filestore_$FECHA.tar.gz -C "$RUTA_INTERNA_FILESTORE" .

# Copiar el filestore al host
docker cp $CONTAINER_WEB:/tmp/filestore_$FECHA.tar.gz $RESPALDO_DIR/odoo_filestore_$FECHA.tar.gz
docker exec -t $CONTAINER_WEB rm /tmp/filestore_$FECHA.tar.gz

if [ -f "$RESPALDO_DIR/odoo_filestore_$FECHA.tar.gz" ]; then
  echo "   -> [✓ FILESTORE] Imágenes y adjuntos respaldados." | tee -a "$LOG_FILE"
else
  echo "   -> [✗ ERROR] Falló el respaldo del filestore." | tee -a "$LOG_FILE"
fi

# 4. COMPRESIÓN FINAL UNIENDO AMBOS EN UN SOLO COMPACTO (.tar.gz)
echo "🗜️ 3/3. Creando paquete de respaldo unificado..." | tee -a "$LOG_FILE"
cd $RESPALDO_DIR
tar -czf odoo_backup_completo_$FECHA.tar.gz odoo_db_$FECHA.sql odoo_filestore_$FECHA.tar.gz

# Limpiar los archivos sueltos temporales en tu Vagrant
rm odoo_db_$FECHA.sql odoo_filestore_$FECHA.tar.gz

echo "==================================================" | tee -a "$LOG_FILE"
echo "🎉 ¡RESPALDO COMPLETADO EXITOSAMENTE!" | tee -a "$LOG_FILE"
echo "📦 Archivo: $RESPALDO_DIR/odoo_backup_completo_$FECHA.tar.gz" | tee -a "$LOG_FILE"
echo "==================================================" | tee -a "$LOG_FILE"
