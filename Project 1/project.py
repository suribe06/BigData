from pyspark.sql import SparkSession, SQLContext
from pyspark.sql.types import *
from pyspark.sql.functions import *
from pyspark.ml.feature import StringIndexer, VectorAssembler
from pyspark.ml.classification import GBTClassifier
from pyspark.streaming import StreamingContext
from pyspark.mllib.evaluation import MulticlassMetrics

spark = SparkSession.builder.appName("AppName").getOrCreate()
spark.sparkContext.setLogLevel('WARN') #Quitar mensajes de INFO

#leer el data set conitniuo desde el csv, cambiar por streaming
df = spark.read.load('adult_set.csv',
                  format='com.databricks.spark.csv',
                  header='true',
                  inferSchema='true').cache()

#valores originales
#print("Filas {0} Columnas {1}".format(df.count(), len(df.columns)))

#data cleaning
df = df.drop("x")
def replace(column, value):
    return when(column != value, column).otherwise(lit(None))

df = df.withColumn("occupation", replace(col("occupation"), "?"))
df = df.withColumn("native_country", replace(col("native_country"), "?"))
df = df.na.drop()

for c in df.columns:
  if(isinstance(df.schema[c].dataType, StringType)):
    indexer = StringIndexer(inputCol= c, outputCol=c.capitalize())
    df = indexer.fit(df).transform(df)

#valores despues del data cleaning
#print("Filas {0} Columnas {1}".format(df.count(), len(df.columns)))

#Machine learning
assemblerAtributos= VectorAssembler(inputCols=["age","Workclass","fnlwgt", "Education", "educational_num", "Marital_status", "Occupation", "Relationship", "Race", "Gender", "capital_gain", "capital_loss","hours_per_week", "Native_country"], outputCol= "Atributos")
dfModificado = assemblerAtributos.transform(df)
dfModificado= dfModificado.select("Atributos","Income")
train, test = dfModificado.randomSplit([0.8,0.2],seed=1) #80% entrenamiento 20% test


#Aplicamos la tecnica de GBT
GPT = GBTClassifier(featuresCol="Atributos", labelCol="Income", maxBins=41)
GPT = GPT.fit(train)
predictions = GPT.transform(test)
results = predictions.select("Income", "prediction")
predictionAndLabels = results.rdd
metrics = MulticlassMetrics(predictionAndLabels)
cm = metrics.confusionMatrix().toArray()
#Calculo de metricas
accuracy = (cm[0][0] + cm[1][1]) / cm.sum()
precision = cm[0][0] / (cm[0][0] + cm[1][0])
recall = cm[0][0] / (cm[0][0] + cm[0][1])
f1 = 2 * ((precision * recall) / (precision + recall))
print("Metricas del modelo GBT Classifier")
print("accuracy = {0}, precision = {1}, recall = {2}, f1 = {3}".format(accuracy, precision, recall, f1))

spark.stop()
