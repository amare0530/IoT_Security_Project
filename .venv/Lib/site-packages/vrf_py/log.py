import logging


# Modify the logging format to include the line number
log_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'

# Create a file handler
file_handler = logging.FileHandler('bot.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(log_format))

# Create a stdout handler
stdout_handler = logging.StreamHandler()
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(logging.Formatter(log_format))

# Get the root logger, set its level, and add both handlers
logger = logging.getLogger() # In funcs, use logger.debug() not logging.debug()
logger.setLevel(logging.INFO)  # Set the root logger's level to DEBUG
logger.addHandler(file_handler)
logger.addHandler(stdout_handler)
