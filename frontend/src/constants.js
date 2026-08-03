// Field definitions mirroring the pydantic model in scripts/api_payload.py.
//
// These bounds are not cosmetic. `perform_data_cleaning` ends in .dropna(),
// so a value outside them is silently discarded server-side rather than
// rejected with a useful message. Keeping the two in sync is asserted by
// tests/e2e/form.spec.js.

export const NUMBER_FIELDS = [
  {
    name: 'distance_km',
    label: 'Distance',
    unit: 'km',
    min: 0.1,
    max: 25,
    step: 0.1,
    hint: 'Straight-line distance from restaurant to customer.',
  },
  {
    name: 'age',
    label: 'Rider age',
    unit: 'years',
    min: 18,
    max: 65,
    step: 1,
    hint: 'Riders under 18 are not represented in the data.',
  },
  {
    name: 'ratings',
    label: 'Rider rating',
    unit: 'of 5',
    min: 1,
    max: 5,
    step: 0.1,
    hint: 'Average customer rating for the rider.',
  },
  {
    name: 'pickup_minutes',
    label: 'Prep & pickup time',
    unit: 'min',
    min: 1,
    max: 60,
    step: 1,
    hint: 'Minutes between the order landing and the rider collecting it.',
  },
  {
    name: 'order_hour',
    label: 'Order hour',
    unit: '24h',
    min: 7,
    max: 23,
    step: 1,
    hint: 'The model has no data for orders between midnight and 07:00.',
  },
];

export const SELECT_FIELDS = [
  {
    name: 'weather',
    label: 'Weather',
    options: ['sunny', 'stormy', 'sandstorms', 'cloudy', 'fog', 'windy'],
  },
  {
    name: 'traffic',
    label: 'Traffic',
    options: ['low', 'medium', 'high', 'jam'],
  },
  {
    name: 'type_of_order',
    label: 'Order type',
    options: ['snack', 'meal', 'drinks', 'buffet'],
  },
  {
    name: 'type_of_vehicle',
    label: 'Vehicle',
    // "bicycle" occurs in the raw dataset but not in the fitted encoder,
    // where it would be silently zero-encoded, so it is not offered.
    options: ['motorcycle', 'scooter', 'electric_scooter'],
  },
  {
    name: 'city_type',
    label: 'City type',
    // "metropolitian" is the dataset's spelling and must be sent verbatim
    options: ['metropolitian', 'urban', 'semi-urban'],
  },
  {
    name: 'festival',
    label: 'Festival day',
    options: ['no', 'yes'],
  },
  {
    name: 'vehicle_condition',
    label: 'Vehicle condition',
    options: ['0', '1', '2', '3'],
    numeric: true,
  },
  {
    name: 'multiple_deliveries',
    label: 'Other deliveries',
    options: ['0', '1', '2', '3'],
    numeric: true,
  },
];

export const DEFAULT_ORDER = {
  distance_km: 7.5,
  age: 28,
  ratings: 4.6,
  pickup_minutes: 10,
  order_hour: 13,
  weather: 'sunny',
  traffic: 'medium',
  type_of_order: 'snack',
  type_of_vehicle: 'motorcycle',
  city_type: 'metropolitian',
  festival: 'no',
  vehicle_condition: 2,
  multiple_deliveries: 1,
};

// Replaces underscores so option values render as readable labels while the
// submitted value stays exactly what the encoder expects.
export const humanize = (value) =>
  value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, ' ');
