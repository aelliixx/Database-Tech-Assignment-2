import csv
from typing import Union

import mysql.connector


class DatabaseManager(object):
    # parse cleaned_data.csv into a list of lists ignoring the header row
    @staticmethod
    def parse_csv():
        with open('flights.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            flights = list(reader)

        with open('iata_codes.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            iata_codes = list(reader)

        return flights, iata_codes

    # Connect to the database
    @staticmethod
    def connect_to_database(addr, usr, pwd):
        try:
            db = mysql.connector.connect(
                host=addr,
                user=usr,
                passwd=pwd
            )
            return db
        except mysql.connector.Error as err:
            raise Exception(err)

    # Check if database exists
    def database_exists(self, db_name):
        self.cursor.execute("SHOW DATABASES LIKE '{}'".format(db_name))
        return self.cursor.fetchone() is not None

    # init
    def __init__(self, addr, usr, pwd, db_name):
        print("\n\n")
        self.db_name = db_name
        try:
            self.db = self.connect_to_database(addr, usr, pwd)
        except Exception as e:
            raise Exception(e)
        self.cursor = self.db.cursor()
        if not self.database_exists(self.db_name):
            self.create_database()
            self.create_iata_codes_table()
            self.create_flights_table()
            self.create_passengers_table()
            self.populate_iata_codes_table()
            self.populate_flights_table()
            self.populate_passengers_table()

        self.cursor.execute("USE {}".format(self.db_name))
        self.select_all_from_table("flights")

    def create_database(self):
        # create database
        self.cursor.execute("CREATE  DATABASE IF NOT EXISTS {}".format(self.db_name))
        self.cursor.execute("USE {}".format(self.db_name))

    # create table for flights
    def create_flights_table(self):
        # fk iata_departure, fk iata_arrival, price, distance
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS flights "
            "(id INT AUTO_INCREMENT PRIMARY KEY, "
            "iata_departure VARCHAR(4), iata_arrival VARCHAR(4), price INT, distance INT, "
            "FOREIGN KEY fk_dep(iata_departure) REFERENCES iata_codes(code), "
            "FOREIGN KEY fk_arr(iata_arrival) REFERENCES iata_codes(code))")

    # create table for passengers
    def create_passengers_table(self):
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS passengers "
            "(id INT AUTO_INCREMENT PRIMARY KEY, "
            "first_name VARCHAR(255), last_name VARCHAR(255), phone VARCHAR(255), flight_id INT, "
            "FOREIGN KEY (flight_id) REFERENCES flights(id))")

    # create table for iata codes
    def create_iata_codes_table(self):
        # pk code (4), city (40), country (40)
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS iata_codes "
            "(code VARCHAR(4) PRIMARY KEY, city VARCHAR(40) NOT NULL, country VARCHAR(40))")

    # populate iata four letter codes table
    def populate_iata_codes_table(self):
        print("Populating iata_codes table...")
        data = self.parse_csv()[1]
        try:
            for code in data:
                self.cursor.execute(
                    "INSERT INTO iata_codes (code, city, country) "
                    "VALUES ('{}', '{}', '{}')".format(code[0], code[1], code[2]))
            self.db.commit()
        except Exception as e:
            print(e)

    # create flights with random dates and prices
    def populate_flights_table(self):
        print("Populating flights table...")
        flights = self.parse_csv()[0]
        # shuffle flights
        import random
        random.shuffle(flights)
        try:
            for flight in flights:
                self.cursor.execute(
                    "INSERT INTO flights (iata_departure, iata_arrival, price, distance) "
                    "VALUES ('{}', '{}', {}, {})".format(flight[1], flight[2], flight[3], flight[4]))
            self.db.commit()
        except Exception as e:
            print(e)

    # populate passengers table
    def populate_passengers_table(self):
        # generate random number of passengers for each flight
        print("Populating passengers table...")
        self.cursor.execute("SELECT id FROM flights")
        flights = self.cursor.fetchall()
        for flight in flights:
            # generate random first and last name
            import requests
            req = requests.get('https://random-data-api.com/api/name/random_name?size=10')
            first_names = [name['first_name'] for name in req.json()]
            last_names = [name['last_name'] for name in req.json()]

            import random
            for i in range(0, random.randint(1, 10)):
                import string
                first_name = first_names[random.randint(0, 9)]
                last_name = last_names[random.randint(0, 9)]
                # generate random phone number
                phone = ''.join(random.choice(string.digits) for _ in range(10))
                self.cursor.execute(
                    "INSERT INTO passengers (first_name, last_name, phone, flight_id) "
                    "VALUES (\"{}\", \"{}\", '{}', {})".format(
                        first_name, last_name, phone, flight[0]))
            self.db.commit()

    def join_iata_with_flights(self):
        query = "SELECT  departure, iata_dep, arrival, iata_arr, price, distance FROM " \
                "( " \
                "SELECT id, flights.iata_departure as departure, iata_codes.city as iata_dep " \
                "FROM flights INNER JOIN iata_codes " \
                "ON flights.iata_departure = iata_codes.code " \
                ") as table1 INNER JOIN " \
                "( " \
                "SELECT id, flights.iata_arrival as arrival, iata_codes.city as iata_arr, " \
                "flights.price as price, flights.distance as distance " \
                "FROM flights INNER JOIN iata_codes " \
                "ON flights.iata_arrival = iata_codes.code " \
                ") as table2 " \
                "ON table1.id = table2.id ORDER BY price DESC"
        self.cursor.execute(query)
        flights = self.cursor.fetchall()
        return flights

    def join_flights_with_passengers(self):
        query = "SELECT " \
                "passengers.first_name, passengers.last_name, " \
                "flights.iata_departure, flights.iata_arrival, flights.price " \
                "FROM passengers INNER JOIN flights " \
                "ON passengers.flight_id = flights.id"
        self.cursor.execute(query)
        passengers = self.cursor.fetchall()
        return passengers

    def get_tables(self):
        self.cursor.execute("SHOW TABLES")
        tables = self.cursor.fetchall()
        tables = [{"name": table[0]} for table in tables]
        return tables

    def select_all_from_table(self, table):
        self.cursor.execute("SELECT * FROM {}".format(table))
        data = self.cursor.fetchall()
        return data

    def average_by(self, group, aggregate, table="flights"):
        query = "SELECT {}, AVG({}) FROM {} GROUP BY {}".format(group, aggregate, table, group)
        self.cursor.execute(query)
        data = self.cursor.fetchall()
        return data

    def average_by_value(self, group, interval, aggregate, table="flights"):
        query = "SELECT ({} DIV {}) as intrvl, AVG({}) FROM {} GROUP BY intrvl ORDER BY intrvl".format(group,
                                                                                                       interval,
                                                                                                       aggregate,
                                                                                                       table)
        self.cursor.execute(query)
        data = self.cursor.fetchall()
        return data

    def get_flight_by_id(self, id):
        query = "SELECT * FROM flights WHERE id = {}".format(id)
        self.cursor.execute(query)
        data = self.cursor.fetchone()
        return data

    def aggregate_average(self, table, aggregate, where):
        query = "SELECT AVG({}) FROM {} WHERE {}".format(aggregate, table, where)
        self.cursor.execute(query)
        data = self.cursor.fetchone()
        return data[0]
