class IATA(object):
    def __init__(self, code, city, country, avg_price, avg_distance):
        self.code = code
        self.city = city
        self.country = country
        self.avg_price = avg_price if avg_price is not None else "N/A"
        self.avg_distance = avg_distance if avg_distance is not None else "N/A "


class Flight(object):
    def __init__(self, iata_departure_code, departure, iata_arrival_code, arrival, price, distance):
        self.iata_departure = iata_departure_code
        self.iata_arrival = iata_arrival_code
        self.departure = departure
        self.arrival = arrival
        self.price = price
        self.distance = distance


class Passenger(object):
    def __init__(self, first_name, last_name, phone, flight):
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.flight_dep = flight[1]
        self.flight_arr = flight[2]
