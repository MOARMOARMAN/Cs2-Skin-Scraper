# CS2 Market Data Pipeline
# Copyright (C) 2026 Charles Wang
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from .utilities import populate_prices_skin_data_db, price_check, get_skin_code_db, SKIN_DATA_DB
import time
import random
import sqlite3
from contextlib import closing

if __name__ == "__main__":
    with closing(sqlite3.connect(SKIN_DATA_DB, timeout=60)) as conn:
        names = [name[0] for name in conn.execute("SELECT skin_name FROM skin_data").fetchall()]

    print(type(names))
    print(names)

    prices = {}

    for name in names:
        fn = price_check(name, 0, get_skin_code_db)
        time.sleep(random.uniform(1, 4))
        mw = price_check(name, 1, get_skin_code_db)
        time.sleep(random.uniform(1, 4))
        ft = price_check(name, 2, get_skin_code_db)
        time.sleep(random.uniform(1, 4))
        ww = price_check(name, 3, get_skin_code_db)
        time.sleep(random.uniform(1, 4))
        bs = price_check(name, 4, get_skin_code_db)
        time.sleep(random.uniform(1, 10))
        prices[name] = [fn, mw, ft, ww, bs]
    populate_prices_skin_data_db(prices, SKIN_DATA_DB)