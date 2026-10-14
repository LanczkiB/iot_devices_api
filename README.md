# iot_devices_api

Design decisions
- Converting Fahrenheit to Celsius when reading the CSV. Only done once on start. Then if the request ask for Fahrenheit values I convert it from Celsius. This way the temperature is stored/handled in a uniform way.