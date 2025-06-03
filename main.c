#include <ArduinoJson.h>

void setup()
{
    Serial.begin(115200);
    while (!Serial)
    {
        ;
    }
}

void loop()
{
    StaticJsonDocument<200> json;
    json["A0"] = analogRead(0);
    json["A1"] = analogRead(1);
    json["A2"] = analogRead(2);
    json["A3"] = analogRead(3);
    json["A4"] = analogRead(4);
    json["A5"] = analogRead(5);

    String output;
    serializeJson(json, output);

    Serial.println(output);

    delay(1000);
}