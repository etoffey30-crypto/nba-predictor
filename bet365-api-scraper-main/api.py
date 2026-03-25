from inplaydiaryapi import InPlays
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.info("Running API script...")
    try:
        in_plays_instance = InPlays()
        result = in_plays_instance.on()
        logging.info(f"Result: {result}")
    except Exception as e:
        logging.error(f'Error: {e}', exc_info=True)

if __name__ == "__main__":
    main()
