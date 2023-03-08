from preprocess import preprocess_streams

INPUT_PATH = "./data/input"
OUTPUT_PATH = "./data/output"
CLIENT_ID = ""
CLIENT_SECRET = ""

with open(file="./auth.txt", mode="r", encoding="UTF-8") as file:
    CLIENT_ID, CLIENT_SECRET = file.readlines()


def main():
    preprocess_streams(INPUT_PATH, OUTPUT_PATH, CLIENT_ID, CLIENT_SECRET)


if __name__ == "__main__":
    main()
