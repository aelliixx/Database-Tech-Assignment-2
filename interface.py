import urwid as u
from database_manager import DatabaseManager
from data_types import Flight, Passenger, IATA

import database_manager


class ListItem(u.WidgetWrap):

    def __init__(self, item, label):
        self.content = item

        # if dict
        if isinstance(item, dict):
            name = item[label]
            # Remove special characters from name
            name = name.replace("_", " ")
            # Capitalise first letter of each word
            name = name.title()
        elif isinstance(item, Flight):
            name = item.iata_departure + " -> " + item.iata_arrival
        elif isinstance(item, Passenger):
            name = item.first_name + " " + item.last_name
        elif isinstance(item, IATA):
            name = item.code

        t = u.AttrWrap(u.Text(name), "country", "country_selected")

        u.WidgetWrap.__init__(self, t)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class ListView(u.WidgetWrap):

    def __init__(self):
        u.register_signal(self.__class__, ['show_details'])

        self.walker = u.SimpleFocusListWalker([])

        lb = u.ListBox(self.walker)

        u.WidgetWrap.__init__(self, lb)

    def modified(self):
        focus_w, _ = self.walker.get_focus()
        u.emit_signal(self, 'show_details', focus_w.content)

    def set_data(self, items, label):
        item_widgets = [ListItem(c, label) for c in items]

        u.disconnect_signal(self.walker, 'modified', self.modified)

        while len(self.walker) > 0:
            self.walker.pop()

        self.walker.extend(item_widgets)

        u.connect_signal(self.walker, "modified", self.modified)

        self.walker.set_focus(0)


class DetailView(u.WidgetWrap):

    def __init__(self):
        t = u.Text("")
        u.WidgetWrap.__init__(self, t)

    def set_country(self, c):
        s = ""
        if isinstance(c, Flight):
            s += "IATA Departure: " + c.iata_departure + "\n"
            s += "Departure: " + c.departure + "\n"
            s += "IATA Arrival: " + c.iata_arrival + "\n"
            s += "Arrival: " + c.arrival + "\n"
            s += "Price: $" + str(c.price) + "\n"
            s += "Distance: " + str(c.distance) + "km\n"
        elif isinstance(c, Passenger):
            s += "First name: " + c.first_name + "\n"
            s += "Last name: " + c.last_name + "\n"
            s += "Phone: +" + c.phone + "\n"
            s += "Flight: " + str(c.flight_dep) + "->" + str(c.flight_arr) + "\n"
        elif isinstance(c, IATA):
            s += "Code: " + c.code + "\n"
            s += "City: " + c.city + "\n"
            s += "Country: " + c.country + "\n"
            s += "Average price to destinations: $" + str(c.avg_price) + "\n"
            s += "Average distance to destinations: " + str(c.avg_distance) + "km\n"
        self._w.set_text(s)


class LogInView(u.WidgetWrap):

    def __init__(self):
        u.register_signal(self.__class__, ['click'])
        self.address_text = u.Text("MySQL Server Address:")
        self.address_edit = u.Edit("> ", edit_text="localhost")
        self.db_name_text = u.Text("Database Name:")
        self.db_name_edit = u.Edit("> ", edit_text="flights")
        self.username_text = u.Text("Username:")
        self.username_edit = u.Edit("> ", edit_text="root")
        self.password_text = u.Text("Password:")
        self.password_edit = u.Edit("> ", mask="*", edit_text="root")
        self.login_text = u.Text("")
        self.login_button = u.Button("Log in", self.log_in)

        form = u.Pile([
            self.address_text,
            self.address_edit,
            self.db_name_text,
            self.db_name_edit,
            self.username_text,
            self.username_edit,
            self.password_text,
            self.password_edit,
            self.login_text,
            self.login_button
        ])

        top = u.Filler(form, valign='middle')

        u.WidgetWrap.__init__(self, top)

    def log_in(self, _):
        try:
            dbm = DatabaseManager(self.address_edit.get_edit_text(), self.username_edit.get_edit_text(),
                                  self.password_edit.get_edit_text(), self.db_name_edit.get_edit_text())
            u.emit_signal(self, 'click', dbm)
        except Exception as e:
            self.login_text.set_text(str(e))


class App(object):

    def unhandled_input(self, key):
        if key in ('q',):
            raise u.ExitMainLoop()

    def show_details(self, item):
        self.detail_view.set_country(item)

    def show_sub_list(self, table):
        info = ""
        lst = []
        if table['name'] == 'flights':
            data = self.dbm.join_iata_with_flights()
            lst = [Flight(data[0], data[1], data[2], data[3], data[4], data[5]) for data in data]
            data_string = "Total number of flights: " + str(len(lst)) + "\n"
            group = self.dbm.average_by_value("distance", 100, "price")
            data_string += "Average price per distance: \n"
            for row in group:
                data_string += ">={}km ${}\n".format(row[0] * 100, int(row[1]))
            info = data_string
        elif table['name'] == 'passengers':
            data = self.dbm.select_all_from_table(table['name'])
            lst = [Passenger(data[1], data[2], data[3],
                             self.dbm.get_flight_by_id(int(data[4]))) for data in data]
            info = "Total passengers: \n" + str(len(lst))
        elif table['name'] == 'iata_codes':
            data = self.dbm.select_all_from_table(table['name'])
            lst = [IATA(data[0], data[1], data[2],
                        self.dbm.aggregate_average("flights", "price", f"iata_departure = '{data[0]}'"),
                        self.dbm.aggregate_average("flights", "distance", f"iata_departure = '{data[0]}'"))
                   for data in data]
            info = "Total airports: \n" + str(len(lst))

        self.info_view.set_text(info)
        self.sub_list_view.set_data(lst, 'name')

    def __init__(self):
        self.dbm = None

        def login(obj):
            self.dbm = obj
            self.update_data()
            self.loop.widget = frame

        self.palette = {
            ("bg", "black", "white"),
            ("country", "black", "white"),
            ("country_selected", "black", "yellow"),
            ("footer", "white, bold", "dark red")
        }

        self.list_view = ListView()
        self.sub_list_view = ListView()
        self.detail_view = DetailView()
        self.info_view = u.Text("")

        u.connect_signal(self.list_view, 'show_details', self.show_sub_list)
        u.connect_signal(self.sub_list_view, 'show_details', self.show_details)

        footer = u.AttrWrap(u.Text(" Q to exit"), "footer")

        col_rows = u.raw_display.Screen().get_cols_rows()
        h = col_rows[0] - 2

        f1 = u.Filler(self.list_view, valign='top', height=h)
        f2 = u.Filler(self.sub_list_view, valign='top', height=h)
        f3 = u.Filler(self.detail_view, valign='top')
        f4 = u.Filler(self.info_view, valign='top')

        c_list = u.LineBox(f1, title="Table")
        s_list = u.LineBox(f2, title="Item")
        c_detail = u.LineBox(f3, title="Details")
        c_info = u.LineBox(f4, title="Info")
        c_details = u.Pile([('weight', 40, c_detail), ('weight', 60, c_info)])

        columns = u.Columns([('weight', 30, c_list), ('weight', 30, s_list), ('weight', 70, c_details)])

        frame = u.AttrMap(u.Frame(body=columns, footer=footer), 'bg')

        self.LogInView = LogInView()
        u.connect_signal(self.LogInView, 'click', login)

        self.loop = u.MainLoop(self.LogInView, self.palette, unhandled_input=self.unhandled_input)

    def update_data(self):
        self.list_view.set_data(self.dbm.get_tables(), 'name')

    def start(self):
        self.loop.run()



