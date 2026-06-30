from db_manager import init_db
from product_manager import get_products
init_db()
for article,cost in get_products(): print(f'{article} | Себестоимость: {cost}')
