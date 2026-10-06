import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler, MinMaxScaler
from tqdm import tqdm

UNPROCESSED_DIR = os.path.join('data', 'unprocessed')
PROCESSED_DIR = os.path.join('data', 'processed')

def load_data(country_code, data_part='train'):
    hhold = os.path.join(UNPROCESSED_DIR, '{}_hhold_{}.csv'.format(country_code, data_part))
    indiv = os.path.join(UNPROCESSED_DIR, '{}_indiv_{}.csv'.format(country_code, data_part))

    hhold = pd.read_csv(hhold, index_col='id')
    indiv = pd.read_csv(indiv, index_col=['id', 'iid'])

    return hhold, indiv

def indiv_vectorize_object_columns(train_data, test_data, agg_type=['mean', 'median', 'any', 'all']):
    '''
        agg_type: ['mean', 'median', 'any', 'all']
    '''
    if 'country' in train_data.columns:
        train_data = train_data.drop('country', axis=1)
    if 'country' in test_data.columns:
        test_data = test_data.drop('country', axis=1)

    train_obj_data = train_data.select_dtypes(include=['object'])
    test_obj_data = test_data[train_obj_data.columns]
    
    train_processed_data = pd.DataFrame()
    test_processed_data = pd.DataFrame()
    
    for col in train_obj_data.columns:
        # Take average of categorical values for each member of the household
        train_group = pd.get_dummies(train_obj_data[col]).reset_index(0).groupby('id')
        test_group = pd.get_dummies(test_obj_data[col]).reset_index(0).groupby('id')

        for at in agg_type:
            if at == 'mean':
                train_vec_feat = train_group.mean()
                test_vec_feat = test_group.mean()
                
            if at == 'median':
                train_vec_feat = train_group.median()
                test_vec_feat = test_group.median()
                
            if at == 'any':
                train_vec_feat = 1 * train_group.any()
                test_vec_feat = 1 * test_group.any()

            if at == 'all':
                train_vec_feat = 1 * train_group.all()
                test_vec_feat = 1 * test_group.all()

            common_cols = train_vec_feat.columns.intersection(test_vec_feat.columns)

            train_vec_feat = train_vec_feat[common_cols]
            test_vec_feat = test_vec_feat[common_cols]

            train_vec_feat.columns = ['{}_{}'.format(at, cname) for cname in train_vec_feat.columns]
            test_vec_feat.columns = ['{}_{}'.format(at, cname) for cname in test_vec_feat.columns]

            if train_processed_data.empty:
                train_processed_data = train_vec_feat
            else:
                train_processed_data = pd.concat([train_processed_data, train_vec_feat], axis=1)

            if test_processed_data.empty:
                test_processed_data = test_vec_feat
            else:
                test_processed_data = pd.concat([test_processed_data, test_vec_feat], axis=1)

    train_processed_data['indiv_count'] = train_data.reset_index(0).groupby('id').count().max(axis=1)
    test_processed_data['indiv_count'] = test_data.reset_index(0).groupby('id').count().max(axis=1)

    return train_processed_data, test_processed_data


def transform_categorical(train, test):
    train = train.copy()
    test = test.copy()

    cols = set(train.columns)
    cat_cols = []
    
    # Target is of bool type so it will not be transformed.
    
    numeric = train.select_dtypes(include=['int64', 'float64'])
    if not numeric.empty:
        numeric_fill = numeric.mean()
        numeric = numeric.fillna(numeric_fill)
        train[numeric.columns] = numeric
        test[numeric.columns] = test[numeric.columns].fillna(numeric_fill)

        sc = StandardScaler()
        mx = MinMaxScaler()

        train = pd.concat(
            [train, pd.DataFrame(
                sc.fit_transform(numeric),
                columns=['sc_{}'.format(i) for i in numeric.columns],
                index=train.index
            )], axis=1)
        
        test = pd.concat(
            [test, pd.DataFrame(
                sc.transform(test[numeric.columns].fillna(numeric_fill)),
                columns=['sc_{}'.format(i) for i in numeric.columns],
                index=test.index
            )], axis=1)
        
        train = pd.concat(
            [train, pd.DataFrame(
                mx.fit_transform(numeric),
                columns=['mx_{}'.format(i) for i in numeric.columns],
                index=train.index
            )], axis=1)
        
        test = pd.concat(
            [test, pd.DataFrame(
                mx.transform(test[numeric.columns].fillna(numeric_fill)),
                columns=['mx_{}'.format(i) for i in numeric.columns],
                index=test.index
            )], axis=1)
    
    for col in tqdm(cols):
        if train[col].dtype == 'object':
            train[col] = train[col].fillna('N/A')
            test[col] = test[col].fillna('N/A')

            train[col] = train[col].apply(str)
            test[col] = test[col].apply(str)

            le = LabelEncoder()

            train_vals = list(train[col].unique())
            test_vals = list(test[col].unique())
            le.fit(train_vals + test_vals)
            train[col] = le.transform(train[col])
            test[col] = le.transform(test[col])
            
            cat_cols.append(col)

    train_ohe = pd.get_dummies(train[cat_cols].astype(str))
    test_ohe = pd.get_dummies(test[cat_cols].astype(str))

    train = pd.concat([train, train_ohe], axis=1)
    test = pd.concat([test, test_ohe], axis=1)
    
    return train, test


if __name__ == '__main__':
    for country_code in ['A', 'B', 'C']:
        print('Processing country {} data...'.format(country_code))
        hhold_train, indiv_train = load_data(country_code, data_part='train')
        hhold_test, indiv_test = load_data(country_code, data_part='test')

        indiv_cat_train, indiv_cat_test = indiv_vectorize_object_columns(indiv_train, indiv_test)

        try:
            indiv_cat_train.to_hdf(os.path.join(PROCESSED_DIR, 'indiv_cat_train.hdf'), '{}_indiv_cat_train'.format(country_code))    
            indiv_cat_test.to_hdf(os.path.join(PROCESSED_DIR, 'indiv_cat_test.hdf'), '{}_indiv_cat_test'.format(country_code))
        except Exception as e:
            print("HDF error, falling back to parquet/csv or tables missing:", e)
            indiv_cat_train.to_csv(os.path.join(PROCESSED_DIR, '{}_indiv_cat_train.csv'.format(country_code)))
            indiv_cat_test.to_csv(os.path.join(PROCESSED_DIR, '{}_indiv_cat_test.csv'.format(country_code)))

        hh_train, hh_test = transform_categorical(hhold_train, hhold_test)

        hh_train.to_csv(os.path.join(PROCESSED_DIR, '{}-hhold-transformed-train.csv'.format(country_code)))
        hh_test.to_csv(os.path.join(PROCESSED_DIR, '{}-hhold-transformed-test.csv'.format(country_code)))

    print("Data processing complete!")
