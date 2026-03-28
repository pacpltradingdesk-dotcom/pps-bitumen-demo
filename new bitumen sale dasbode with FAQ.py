import distance_matrix
import sys

# Set unicode encoding for console output to avoid errors
sys.stdout.reconfigure(encoding='utf-8')

print("--- City Data Verification ---")

# 1. Check Stats
cities_count = len(distance_matrix.DESTINATIONS)
states_count = len(distance_matrix.ALL_STATES)
coords_count = len(distance_matrix.DESTINATION_COORDS)

print(f"Total Cities: {cities_count}")
print(f"Total States: {states_count}")
print(f"Cities with Coordinates: {coords_count}")

if cities_count != coords_count:
    print("ERR: City count mismatch with coordinates!")
    print(f"Cities without coords: {set(distance_matrix.DESTINATIONS) - set(distance_matrix.DESTINATION_COORDS.keys())}")
else:
    print("City - Coordinate Mapping OK")

# 2. Check State Mapping
valid_mapping = True
missing_states = []
for city in distance_matrix.DESTINATIONS:
    if city not in distance_matrix.CITY_STATE_MAP:
        valid_mapping = False
        missing_states.append(city)

if valid_mapping:
    print("All cities have state mappings")
else:
    print(f"ERR: Missing state mappings for: {missing_states}")

# 3. Test Distance Calculation
test_pairs = [
    ("IOCL Koyali", "Vadodara"), # Close
    ("Kandla Port Import", "Ludhiana"), # Long distance
    ("BPCL Mumbai", "Pune")
]

print("\n--- Distance Tests ---")
for src, dst in test_pairs:
    dist = distance_matrix.get_distance(src, dst)
    print(f"{src} -> {dst}: {dist} km")

print("\n--- State Check ---")
guj_cities = distance_matrix.get_cities_by_state("Gujarat")
print(f"Gujarat Cities ({len(guj_cities)}): {guj_cities[:5]} ...")

if len(guj_cities) > 5:
    print("State filtering working")
