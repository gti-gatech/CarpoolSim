import pandas as pd
from sqlalchemy import create_engine
import pickle


# helper method for multiprocessing
# move this code in somewhere else for multiprocessing
def batch_store_from_name(pk_name, url):
    db1 = {'dist': {}, 'path': {}}
    with open(pk_name, 'rb') as dbfile:
        db_temp = pickle.load(dbfile)
        db1['dist'] = {**db_temp['dist']}
        db1['path'] = {**db_temp['path']}
    batch_store_df(db1, url)


def sql_engine_factory(db_url):
    db_type = db_url.split(":")[0]
    if db_type == "sqlite":
        engine = create_engine(
            db_url,
            connect_args={'timeout': 30}
        )
    elif db_type == "postgresql":
        engine = create_engine(
            db_url,
            connect_args={'connect_timeout': 30}
        )
    else:
        raise IOError(f"engine type {db_type} not recognized...")
    return engine


def batch_store_df(db1, url):
    engine = sql_engine_factory(url)
    dists_df = pd.DataFrame(
        convert_dict_to_row(db1['dist']),
        columns=['origin', 'destination', 'dists']
    )
    db1['dist'] = {}  # delete dict in time to save memory
    paths_df = pd.DataFrame(
        convert_dict_to_row(db1['path'], last_column_type='str'),
        columns=['origin', 'destination', 'paths']
    )
    del db1
    paths_df['paths'] = paths_df['paths'].astype('str')

    paths_df.set_index(['origin', 'destination'], inplace=True)
    dists_df.set_index(['origin', 'destination'], inplace=True)
    dists_df = dists_df.join(paths_df)
    del paths_df
    print("start feeding data to database! Dataframe shape: ", dists_df.shape)
    with engine.connect() as connection:
        dists_df.to_sql(
            'dists', con=connection,
            method='multi', if_exists='append',
            chunksize=50
        )
    print("Appended a whole batch data to the server!")
    del dists_df


def convert_dict_to_row(dt, last_column_type=None):
    dt_lst = list()
    if last_column_type is None:
        for dt_key in dt:
            orig_taz = dt_key
            inner_dict = dt[dt_key]
            for key in inner_dict:
                dest_taz, dest_dist = key, inner_dict[key]
                dt_lst.append((orig_taz, dest_taz, dest_dist))
    else:
        for dt_key in dt:
            orig_taz = dt_key
            inner_dict = dt[dt_key]
            for key in inner_dict:
                dest_taz, dest_dist = key, inner_dict[key]
                dt_lst.append((orig_taz, dest_taz, str(dest_dist)))
    return dt_lst
