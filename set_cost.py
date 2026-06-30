from db_manager import init_db
from product_manager import set_cost_price
init_db(); set_cost_price(input('Артикул: '), float(input('Себестоимость: ')))
print('Себестоимость сохранена')
