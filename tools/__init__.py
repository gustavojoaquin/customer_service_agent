from .flights_tools import (
    fetch_user_flight_information,
    search_flights,
    cancel_ticket,
    update_ticket_to_new_flight,
    register_new_flight
)

from .car_tools import (
    search_car_rentals,
    book_car_rental,
    cancel_car_rental,
    buscar_carros_rentados
)

from .hotel_tools import (
    search_hotels,
    book_hotel,
    cancel_hotel
)

from .excursion_tools import (
    search_trip_recommendations,
    book_excursion,
    cancel_excursion
)

from .policy_tools import lookup_policy




primary_assistant_tools = [ fetch_user_flight_information, lookup_policy]

flight_safe_tools = [search_flights, lookup_policy]
flight_sensitive_tools = [
    update_ticket_to_new_flight,
    cancel_ticket,
    register_new_flight,
]

car_rental_safe_tools = [search_car_rentals,buscar_carros_rentados, lookup_policy]
car_rental_sensitive_tools = [book_car_rental, cancel_car_rental]

hotel_safe_tools = [search_hotels, lookup_policy]
hotel_sensitive_tools = [book_hotel, cancel_hotel]

excursion_safe_tools = [search_trip_recommendations, lookup_policy]
excursion_sensitive_tools = [book_excursion, cancel_excursion]


