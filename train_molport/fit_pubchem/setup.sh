#python3 ../../job_scripts.py job.params  -b bridges_fit.sh -o . -n '{gen_model_name}_{disc_model_name}_{train_seed}_{train_iter}_{gen_options}_{data_name}'
python3 ../../job_scripts.py post.params  -t crc_fit.sh -n '{gen_model_name}_{disc_model_name}_{train_seed}_{train_iter}_{gen_options}_{data_name}'
python3 ../../job_scripts.py prior.params -t crc_fit.sh -n '{gen_model_name}_{disc_model_name}_{train_seed}_{train_iter}_{gen_options}_{data_name}'
