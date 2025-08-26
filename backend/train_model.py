import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
import os

# =========================
# 1. กำหนดค่าพื้นฐาน
# =========================
IMG_WIDTH, IMG_HEIGHT = 160, 160
BATCH_SIZE = 32
EPOCHS = 20
DATA_DIR = 'dataset/train'
MODEL_SAVE_PATH = 'models/sign_model.h5'

os.makedirs('models', exist_ok=True)

# =========================
# 2. เตรียมข้อมูล
# =========================
datagen = ImageDataGenerator(
    rescale=1./255,
    validation_split=0.2
)

train_generator = datagen.flow_from_directory(
    DATA_DIR,
    target_size=(IMG_WIDTH, IMG_HEIGHT),
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    subset='training'
)

validation_generator = datagen.flow_from_directory(
    DATA_DIR,
    target_size=(IMG_WIDTH, IMG_HEIGHT),
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    subset='validation'
)

num_classes = len(train_generator.class_indices)

# =========================
# 3. โหลด MobileNetV2
# =========================
base_model = MobileNetV2(
    input_shape=(IMG_WIDTH, IMG_HEIGHT, 3),
    include_top=False,
    weights='imagenet'
)
base_model.trainable = False   # เทรนเฉพาะ head ก่อน

x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(256, activation='relu')(x)
x = Dropout(0.5)(x)
predictions = Dense(num_classes, activation='softmax')(x)

model = Model(inputs=base_model.input, outputs=predictions)

# =========================
# 4. คอมไพล์โมเดล
# =========================
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# =========================
# 5. Callback
# =========================
early_stop = EarlyStopping(
    monitor='val_loss',
    patience=3,
    restore_best_weights=True
)

checkpoint = ModelCheckpoint(
    MODEL_SAVE_PATH,
    monitor='val_accuracy',
    save_best_only=True,
    verbose=1
)

# =========================
# 6. Train
# =========================
history = model.fit(
    train_generator,
    epochs=EPOCHS,
    validation_data=validation_generator,
    callbacks=[early_stop, checkpoint]
)

# =========================
# 7. Save
# =========================
model.save(MODEL_SAVE_PATH)
print(f"\n✅ Training finished! Model saved to: {MODEL_SAVE_PATH}")
