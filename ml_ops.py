# -*- coding: utf-8 -*-
"""ML_OPS.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1IWWuI0RwUEe_nRyklsFdgiCbd43mSPfY

# PACKAGES / IMPORT
"""

#-------------------------------------------------------------------#
# Importer tous les packages permettant d'utiliser spark et pyspark #
#-------------------------------------------------------------------#

!apt-get install openjdk-8-jdk-headless -qq > /dev/null
!wget -q http://archive.apache.org/dist/spark/spark-3.1.1/spark-3.1.1-bin-hadoop3.2.tgz
!tar xf spark-3.1.1-bin-hadoop3.2.tgz
!pip install -q findspark

import os
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-8-openjdk-amd64"
os.environ["SPARK_HOME"] = "/content/spark-3.1.1-bin-hadoop3.2"

import findspark
findspark.init()
from pyspark.sql import SparkSession
spark = SparkSession.builder.master("local[*]").getOrCreate()

# Importations de quelques fonctions SQL
import pyspark.sql.functions as f
from pyspark.sql.functions import *
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

#--------#
# Python #
#--------#

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

!pip install h2o

import h2o
from h2o.automl import H2OAutoML

# End

TRAIN = spark.read.csv('/content/sample_data/california_housing_train.csv', header=True, inferSchema=True)
TEST = spark.read.csv('/content/sample_data/california_housing_test.csv', header=True, inferSchema=True)

TRAIN.createOrReplaceTempView('TRAIN')
TEST.createOrReplaceTempView('TEST')

"""# DATA CLEANING"""

TRAIN.printSchema()

TRAIN.show(5)

n = TRAIN.count()
MISSING_DATA = TRAIN.select( [ (count(when(isnull(X),1))/n) \
              .alias(X) for X in TRAIN.columns] )\
              .toPandas().T # Converting to pandas DataFrame that allow transposing

MISSING_DATA.rename(columns={0 :'PCT_MISS'}, inplace=True)
print(MISSING_DATA.sort_values(by='PCT_MISS',ascending=False))

sample = TRAIN.sample(withReplacement=False, fraction=0.10)

sample_df = sample.toPandas()
sample_df.describe(percentiles=[.01,.25,.75,.95,.99]).T

"""# MACHINE LEARNING"""

# Split TRAIN / TEST into Pandas

train_df = TRAIN.toPandas()
test_df = TEST.toPandas()

# Using AutoML with H20
h2o.init()

# Converting DataFrames Pandas into H2OFrames
h2o_train = h2o.H2OFrame(train_df)
h2o_test = h2o.H2OFrame(test_df)

Y = "median_house_value"
X = h2o_train.columns
X.remove(Y)

aml = H2OAutoML(max_models=10,
                max_runtime_secs=300 ,
                seed=123,
                sort_metric='RMSE',
                stopping_metric='AUTO', # Stop Log_Loss
                nfolds=5)
aml.train(x=X,
          y=Y,
          training_frame=h2o_train,
          validation_frame=h2o_test)

lb_aml = aml.leaderboard
print(lb_aml)

perf = aml.leader.model_performance(test_data=h2o_test)
print(perf)



"""# Nouvelle section"""

# Missing Data

total_rows = TRAIN.count()
missing_list= []

for col in TRAIN.columns:
  query = f"""
          SELECT DISTINCT
          '{col}' AS NAME_VAR,
          (SUM(CASE WHEN '{col}' IS NULL OR ISNAN('{col}') THEN 1 ELSE 0 END))*1.00/'{total_rows}' AS MISSING_PCT
          FROM TRAIN
      """
  result = spark.sql(query).collect()[0] # First (and unique) row at each iteration
  missing_list.append((result.NAME_VAR, result.MISSING_PCT)) # append result at each iteration