import tensorflow as tf

# Carica il modello Keras
model = tf.keras.models.load_model('model.h5')

# Converti il modello Keras in un modello TensorFlow Lite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

# Salva il modello TensorFlow Lite su disco
with open('model.tflite', 'wb') as f:
    f.write(tflite_model)

# Carica il modello TensorFlow Lite
interpreter = tf.lite.Interpreter(model_content=tflite_model)
interpreter.allocate_tensors()

# Puoi ora utilizzare l'interprete per eseguire inferenza sui dati di input
# Vedi la documentazione di TensorFlow Lite per ulteriori dettagli sull'esecuzione dell'inferenza
