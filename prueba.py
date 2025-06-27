import pandas as pd
import matplotlib.pyplot as plt
# Configuración warnings
import warnings
warnings.filterwarnings('ignore')


# Leer fuente de datos
CSV_FILE_PATH = "Violencia_clean.csv"
df = pd.read_csv(CSV_FILE_PATH, sep=",")


# print(df["Presunto Agresor"].astype('category'))

# GRAFICO DE BARRAS PARA LA COLUMNAY "Departamento"
frec = df["Presunto Agresor"].value_counts()
frec.plot(kind="bar")
plt.xticks(rotation=80)
plt.show()