import traci
import traci.constants as tc

class StatisticsProbe:
    def __init__(self, bus_depot_end_edge):
        self.bus_depot_end_edge = bus_depot_end_edge
        self.last_step_stats = StepStats(0)
        self.step_stats = {}
        self.step_stats[0] = self.last_step_stats
        self.waiting_time_per_person = {}
        self.arrived_people = set()
        self.bus_id_to_type = {}
        self.distence_per_bus = {}
        self.edge_per_bus = {}
        self.buses_not_at_depot = []

    def measure(self, step: int):
        step_stats = StepStats(step)
        self.step_stats[step] = step_stats

        # count number of people waiting and their waiting time
        person_ids = traci.person.getIDList()
        for person_id in person_ids:
            stage = traci.person.getStage(person_id)            
            if stage.description == 'waiting for ANY':
                step_stats.number_of_people_waiting += 1
                waiting_time = traci.person.getWaitingTime(person_id)
                self.waiting_time_per_person[person_id] = waiting_time
            if stage.description == 'driving':
                step_stats.number_of_people_driving += 1
            if stage.description == 'waiting (Arrived at destination)':
                self.arrived_people.add(person_id)

        for person_id in self.arrived_people:
            step_stats.total_waiting_time += self.waiting_time_per_person[person_id]
            step_stats.number_of_people_arrived += 1
        step_stats.number_of_people_total = len(self.waiting_time_per_person)

        # count number of buses of each type and their distance driven
        vehicle_ids = traci.vehicle.getIDList()

        # check for buses that where removed and keep their last edge
        for vehicle_id in list(self.edge_per_bus.keys()):
            if vehicle_id in vehicle_ids:
                # bus is still present in simulation
                continue

            # check if bus arrived at bus depot
            final_edge = self.edge_per_bus[vehicle_id]
            if final_edge != self.bus_depot_end_edge:
                self.buses_not_at_depot.append(vehicle_id)
            self.edge_per_bus.pop(vehicle_id)

        # count number of busses of each type, get their distance, and track their current edge
        for vehicle_id in vehicle_ids:
            type_id = traci.vehicle.getTypeID(vehicle_id)
            if type_id == 'DEFAULT_VEHTYPE': 
                # skip 'normal' cars
                continue

            # keep track of bus type
            self.bus_id_to_type[vehicle_id] = type_id

            # distance
            distance = traci.vehicle.getDistance(vehicle_id)
            self.distence_per_bus[vehicle_id] = distance / 1000.0 # convert to km

            # bus count
            if type_id == 'BUS_S': 
                step_stats.number_of_buses_s += 1
            elif type_id == 'BUS_M': 
                step_stats.number_of_buses_m += 1
            elif type_id == 'BUS_L': 
                step_stats.number_of_buses_l += 1
            else: 
                raise Exception(f'Unsupported vehicle type {type_id}')

            # current edge
            edge_id = traci.vehicle.getRoadID(vehicle_id)
            self.edge_per_bus[vehicle_id] = edge_id

        # check buses that aren't remove at bus depot location
        for vehicle_id in self.buses_not_at_depot:
            type_id = self.bus_id_to_type[vehicle_id]
            if type_id == 'BUS_S': 
                step_stats.number_of_buses_s += 1
            elif type_id == 'BUS_M': 
                step_stats.number_of_buses_m += 1
            elif type_id == 'BUS_L': 
                step_stats.number_of_buses_l += 1

        # check if current bus counts are lower then counts in last step
        if self.last_step_stats.number_of_buses_s > step_stats.number_of_buses_s:
            step_stats.number_of_buses_s = self.last_step_stats.number_of_buses_s
        if self.last_step_stats.number_of_buses_m > step_stats.number_of_buses_m:
            step_stats.number_of_buses_m = self.last_step_stats.number_of_buses_m
        if self.last_step_stats.number_of_buses_l > step_stats.number_of_buses_l:
            step_stats.number_of_buses_l = self.last_step_stats.number_of_buses_l

        # sum up total distance for each bus type
        for vehicle_id, distance in self.distence_per_bus.items():
            type_id = self.bus_id_to_type[vehicle_id]
            if type_id == 'BUS_S': 
                step_stats.total_distance_buses_s += distance
            if type_id == 'BUS_M': 
                step_stats.total_distance_buses_m += distance
            if type_id == 'BUS_L': 
                step_stats.total_distance_buses_l += distance

        self.last_step_stats = step_stats

    def write_results(self, out_file: str, step0: int, step_delta: int):
        with open(out_file, 'w') as f:
            line = self.dump_header()
            f.write("%s\n" % line)
            for step in range(step0, self.last_step_stats.step, step_delta):
            # for step in self.step_stats:
                line = self.dump(step)
                f.write("%s\n" % line)

    def dump_header(self):
        return "step;" + \
            "number_of_people_total;number_of_people_arrived;number_of_people_driving;number_of_people_waiting;" + \
            "total_waiting_time;" + \
            "number_of_buses_s;number_of_buses_m;number_of_buses_l;" + \
            "total_distance_buses_s;total_distance_buses_m;total_distance_buses_l"

    def dump(self, step: int):
        return self.step_stats[step].to_csv_line()


class StepStats:
    def __init__(self, step: int):
        self.step = step
        self.number_of_people_total = 0
        self.number_of_people_arrived = 0
        self.number_of_people_driving = 0
        self.number_of_people_waiting = 0
        self.total_waiting_time = 0.0
        self.number_of_buses_s = 0
        self.number_of_buses_m = 0
        self.number_of_buses_l = 0
        self.total_distance_buses_s = 0.0
        self.total_distance_buses_m = 0.0
        self.total_distance_buses_l = 0.0

    def to_csv_line(self):
        return "{};{};{};{};{};{};{};{};{};{:f};{:f};{:f}".format(\
            self.step, \
            self.number_of_people_total, \
            self.number_of_people_arrived, \
            self.number_of_people_driving, \
            self.number_of_people_waiting, \
            self.total_waiting_time, \
            self.number_of_buses_s, \
            self.number_of_buses_m, \
            self.number_of_buses_l, \
            self.total_distance_buses_s, \
            self.total_distance_buses_m, \
            self.total_distance_buses_l)