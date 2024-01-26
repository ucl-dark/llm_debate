import argparse

from web.backend.services.import_data import import_csv, import_dir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="csv file to import")
    parser.add_argument("--dir", help="directory to import")
    args = parser.parse_args()
    if args.file:
        import_csv(args.file)
    elif args.dir:
        import_dir(args.dir)
    else:
        raise ValueError("Must specify either --file or --dir")


if __name__ == "__main__":
    main()
