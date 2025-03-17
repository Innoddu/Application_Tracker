import tensorflow as tf
import tensorflow_transform as tft
from tfx.components.trainer.fn_args_utils import FnArgs
from tfx_bsl.public import tfxio
from tensorflow_transform.tf_metadata import schema_utils
from tensorflow_metadata.proto.v0 import schema_pb2

# Define feature keys
FEATURE_KEYS = ['has_subject_keyword', 'applying', 'application', 'reviewing', 'decided', 'interest', 'received', 'moving forward', 'regret', 'resume']
LABEL_KEY = 'isApplication'

# Function to detect keywords in the subject
def keyword_subject(inputs):
    keywords = ["carefully review", 'thank you for submitting your resume', 'thanks for completing your application', 'thank you for your interest', 'thank you from', 'application received', 'thank you for your application', 'application submitted to', 'thank you for applying', 'thanks for applying', 'thank you for applying with', 'submitting your application', 'reviewing your resume', 'received your application']
    subject = tf.sparse.to_dense(inputs['subject'], default_value='')
    has_subject_keyword = tf.reduce_any([tf.strings.regex_full_match(subject, f".*{keyword}.*") for keyword in keywords], axis=0)
    return tf.cast(has_subject_keyword, tf.float32)

# Function to check for word presence in texts
def words_in_texts(words, texts):
    texts = tf.sparse.to_dense(texts, default_value='')
    indicator_array = [tf.strings.regex_full_match(texts, f".*{word}.*") for word in words]
    return tf.stack(indicator_array, axis=1)

# Preprocessing function
def preprocessing_fn(inputs):
    outputs = inputs.copy()
    has_subject_keyword = keyword_subject(inputs)
    outputs['has_subject_keyword'] = tf.reshape(has_subject_keyword, [-1, 1])
    keywords = ['applying', 'application', 'reviewing', 'decided', 'interest', 'received', 'moving forward', 'regret', 'resume']
    word_indicators = words_in_texts(keywords, inputs['body'])
    for i, keyword in enumerate(keywords):
        outputs[keyword] = tf.reshape(tf.cast(word_indicators[:, i], tf.float32), [-1, 1])
    for feature in ['has_subject_keyword'] + keywords:
        outputs[feature] = tft.scale_to_z_score(outputs[feature])
    return outputs

# Build Keras model function
def _build_keras_model():
    inputs = {
        key: tf.keras.layers.Input(name=key, shape=(1,), dtype=tf.float32)
        for key in FEATURE_KEYS
    }
    concatenated_inputs = tf.keras.layers.Concatenate()(list(inputs.values()))
    x = tf.keras.layers.Dense(10, activation='relu')(concatenated_inputs)
    outputs = tf.keras.layers.Dense(1, activation='sigmoid')(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

# Trainer function
def run_fn(fn_args: FnArgs):
    tf_transform_output = tft.TFTransformOutput(fn_args.transform_output)
    
    def _input_fn(file_pattern, batch_size):
        dataset = tf.data.TFRecordDataset(file_pattern)
        feature_spec = tf_transform_output.transformed_feature_spec()
        
        def _parse_function(proto):
            parsed_features = tf.io.parse_single_example(proto, feature_spec)
            inputs = {key: parsed_features[key] for key in FEATURE_KEYS}
            label = parsed_features[LABEL_KEY]
            return inputs, label
        
        dataset = dataset.map(_parse_function)
        dataset = dataset.batch(batch_size)
        return dataset
    
    train_dataset = _input_fn(fn_args.train_files, 40)
    eval_dataset = _input_fn(fn_args.eval_files, 40)
    
    model = _build_keras_model()
    model.fit(
        train_dataset,
        steps_per_epoch=fn_args.train_steps,
        validation_data=eval_dataset,
        validation_steps=fn_args.eval_steps
    )
    model.save(fn_args.serving_model_dir, save_format='tf')
