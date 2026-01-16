
DB='data/db/cec.db'

#remove old db
echo 'Deleting old db...'
rm -f "$DB"

#rebuild
echo 'Rebuilding...'
sqlite3 "$DB" < schema.sql

#populate
echo 'populating with updated csv...'
python3 import.py

echo "Done"
