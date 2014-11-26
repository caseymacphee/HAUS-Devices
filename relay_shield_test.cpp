/*
 # This Sample code is for testing the Relay shield V2.1 for Arduino.
   
 # Editor : Phoebe
 # Date   : 2013.2.28
 # Ver    : 0.1
 # Product: Relay shield for Arduino
 # SKU    : DRI0144
    
 # Hardwares:
 1. Arduino UNO
 2. Relay Shield For Arduino V2.1 
 3  Power Supply:7~ 12V
 */
 
byte relayPin[4] = {
  2,7,8,10};
//D2 -> RELAY1
//D7 -> RELAY2
//D8 -> RELAY3
//D10 -> RELAY
char input=0;
int val;
 
void setup() {
  for(int i = 0; i < 4; i++)  pinMode(relayPin[i],OUTPUT);
  Serial.begin(9600); 
  delay(100); 
  for(int j = 0; j < 4; j++)  digitalWrite(relayPin[j],LOW);
}
 
void loop() {
  if (Serial.available()) 
  {  
    char input= Serial.read();  
    if(input != -1)
    {
      int state;
      Serial.print("$");
      switch(input)
      {
      case '1':        
        Serial.print("Relay1=");
        val=digitalRead(relayPin[0]);
        val=!val;
        digitalWrite(relayPin[0],val);
        state = digitalRead(relayPin[0]);
        break;
      case '2':
        Serial.print("Relay2=");
        state = digitalRead(relayPin[1]);
        val=digitalRead(relayPin[1]);
        val=!val;
        digitalWrite(relayPin[1],val);
        break;
      case '3':
        Serial.print("Relay3=");
        val=digitalRead(relayPin[2]);
        val=!val;
        digitalWrite(relayPin[2],val);
        break;
      case '4':
        Serial.print("Relay4=");
        val=digitalRead(relayPin[3]);
        val=!val;
        digitalWrite(relayPin[3],val);
        break;
      case '$':
        val = digitalRead(relayPin[0]);
        Serial.print("Relay1=");
        Serial.print(val);
        for(int i = 1; i < 4; i ++){
          Serial.print(",Relay");
          Serial.print(i);
          Serial.print("=");
          val = digitalRead(relayPin[i]);
          Serial.print(val);
          }
         break;
      default:
        if(input != '\r' && input != '\n')
        Serial.println("invalid entry");
        break;
     
      }
      Serial.println("#");
    }
  }
}