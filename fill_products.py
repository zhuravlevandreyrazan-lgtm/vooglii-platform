from db_manager import init_db
from product_manager import sync_products_from_sales, get_products
init_db(); sync_products_from_sales()
for row in get_products(): print(row)
