from database.data_loader import load_foods


def main():
    foods = load_foods()

    print(foods.head())
    print(foods.shape)


if __name__ == "__main__":
    main()