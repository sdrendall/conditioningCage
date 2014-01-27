

// Home Cage Conditioning
//
// v 1.3
// Nov. 2013
//
// Ofer Mazor and Sam Rendall


#include "HCFC_Pins.h"


// buffer for reading lines of text from USB
String serialLine;

// globals for debugging:
const int BUFF_LEN = 1024;
char charBuffer[BUFF_LEN];
unsigned long int startTime=0;
int onBoardLED = 6; // for debugging

// globals for temperature reading
unsigned long int nextTempTime;
unsigned long int nextTempLogTime;

// globals for conditioning
const int MAX_BLOCKS = 128;
int numBlocks = 0;
unsigned long int endFCBlockTime; // in millis
unsigned long int startFCToneTime; // in millis
unsigned long int startFCShockTime; // in millis
int currentFCBlockIndex = 0;
boolean inFearConditioningMode;
boolean toneOn = false;
boolean shockOn = false;

// globals for nose poke
boolean nosepokeOnStandby = true;
unsigned long int nosepokeCount = 0;
unsigned long int waterDeliveryCount = 0;
unsigned long int solenoidClosingTime;
boolean solenoidOpen = false;

// DEBUG and ERROR outputs to USB
void debugOut(String debugText) {
  double time = (millis() - startTime)/1000.0;
  Serial.print("[DEBUG] [Time: ");
  Serial.print(time,1);
  Serial.print("] ");
  debugText.toCharArray(charBuffer, BUFF_LEN);
  Serial.println(charBuffer);
}
void errorOut(String errorText) {
  errorText = String("Error: ") + errorText;
  errorText.toCharArray(charBuffer, BUFF_LEN);
  Serial.println(charBuffer);
}

// LOG Data to USB
void logData(String dataName, long dataValue) {
  double time = (millis() - startTime)/1000.0;
  Serial.print("LOG ");
  dataName.toCharArray(charBuffer, BUFF_LEN);
  Serial.print(charBuffer);
  Serial.print(": ");
  Serial.println(dataValue,DEC);
}


// Parameter Structure
// This is for user-specified parameters to
// be updated over USB.
// Default values are set here.
struct Parameters {
  unsigned long int tempPeriod; // how often to check temperature (in ms)
  unsigned long int tempLogPeriod; // how often to log temperature (in ms)
  unsigned long int toneDuration; // in ms
  unsigned long int shockDuration; // in ms
  unsigned long int dispensationInterval; // in ms
  float targetTemp;   //Desired Cage temperature in Celcius
  boolean tmp2_active;
  unsigned long int fcToneFrequency;
  // array of block durations:
  unsigned long int BlockDuration[MAX_BLOCKS]; // in ms
};
Parameters parameters;


void initParams() {
  parameters.tempPeriod = 5000; // how often to check temperature (in ms)
  parameters.tempLogPeriod = 60000; // how often to check temperature (in ms)
  parameters.BlockDuration[0] = 5000;
  parameters.BlockDuration[1] = 10000;
  parameters.BlockDuration[2] = 15000;
  numBlocks = 3; // this is a global -- not part of parameters
  parameters.toneDuration = 3000;
  parameters.shockDuration = 1000;
  parameters.dispensationInterval = 100;
  parameters.targetTemp = 33.0;
  parameters.tmp2_active = false;
  parameters.fcToneFrequency = 6000;
}

void printParams() {
  // TODO loop on parameters and log them
}

// Start the fear conditioning protocol
void runFC() {
  startTime = millis();
  inFearConditioningMode = true;
  currentFCBlockIndex = 0;
  runFCBlock(currentFCBlockIndex);
}

void runFCBlock(int blockNum) {
  currentFCBlockIndex = blockNum;
  turnToneOff();
  turnShockOff();
  if (blockNum >= numBlocks) {
    debugOut("End of blocks");
    currentFCBlockIndex = 0;
    logData(String("FC"), 0);
    inFearConditioningMode = false;
  } else {
    debugOut(String("Block ")+(blockNum+1));
    logData(String("FC"), blockNum+1);
    unsigned long int blockStartTime = millis();
    unsigned long int blockDuration = parameters.BlockDuration[currentFCBlockIndex];
    unsigned long int toneDuration = parameters.toneDuration;
    unsigned long int shockDuration = parameters.shockDuration;
    endFCBlockTime = blockStartTime + blockDuration;
    if (toneDuration >= blockDuration) {
      turnToneOn();
    } else if (toneDuration == 0){
      startFCToneTime = endFCBlockTime + 60000; // never play tone
    } else {
      startFCToneTime = endFCBlockTime - parameters.toneDuration;
    }
    if (shockDuration >= blockDuration) {
      turnShockOn();
    } else if (shockDuration == 0){
      startFCShockTime = endFCBlockTime + 60000; // never play tone
    } else {
      startFCShockTime = endFCBlockTime - parameters.shockDuration;
    }
  }
}


// read all available chars to a buffer and interpret any complete lines
void readAndInterpretAvailableChars() {
    while (Serial.available() > 0){
    // read any available characters
    char ch = Serial.read();
    if (ch == '\n') {
      // read any available characters
      interpretInputString(serialLine);
      serialLine = "";
      break; // don't interpret more than one line before returning
    } else {
      serialLine += ch;
    }
  }
}

// Interpret one line of input from USB
void interpretInputString(String input) {

  // debugOut(input);

  input.trim(); // remove leading & trailing whitespace

  if (input.length()==1) {
    // special commands
    debugOut(String("Command: ")+input);
    switch (input[0]) {
      case 'F': // Run Fear Conditioning
        debugOut(String("Run FC"));
        runFC();
        break;
      case 'X': // Stop Fear Conditioning
        debugOut(String("Abort FC"));
        currentFCBlockIndex = numBlocks;
        runFCBlock(currentFCBlockIndex);
        break;
      case 'P': // Output current parameter values
        printParams();
        break;
      case 'R':
        // reset nosepoke / water counts
        nosepokeCount = 0;
        waterDeliveryCount = 0;
        break;
      case 'S':
        // get cage state
        logData("FC", (int)inFearConditioningMode*(currentFCBlockIndex+1));
        logData("Tone", toneOn);
        logData("Shock", shockOn);
        logData("Nose", nosepokeCount);
        logData("Water", waterDeliveryCount);
        logData("Temp",  checkTMP(TMP1_PIN));
        break;
      default:
        break;
    }

  } else if (input.indexOf(':') > -1) {
     // parameter value
    int i = input.indexOf(':');
    String pName = input.substring(0, i);
    String pVal_s = input.substring(i+1);
    pVal_s.trim();
    long int pVal = pVal_s.toInt();
    // TODO: accept float parameters

    debugOut("Set param value:");
    debugOut(String("\"")+pName+"\" --> "+pVal);

    if (pName == "tempPeriod") {
      parameters.tempPeriod = pVal;
    } else if (pName == "tempLogPeriod") {
      parameters.tempLogPeriod = pVal;
    } else if (pName == "toneDuration") {
      parameters.toneDuration = pVal;
    } else if (pName == "shockDuration") {
      parameters.shockDuration = pVal;
    } else if (pName == "dispensationInterval") {
      parameters.dispensationInterval = pVal;
    } else if (pName == "targetTemp") {
      parameters.targetTemp = pVal;
    } else if (pName == "tmp2_active") {
      parameters.tmp2_active = pVal;
    } else if (pName == "fcToneFrequency") {
      parameters.fcToneFrequency = pVal;
    } else if (pName == "BlockDuration") {
      String blockDurationsString = pVal_s;
      numBlocks = 0;
      while (blockDurationsString.toInt() > 0) {
        parameters.BlockDuration[numBlocks] = blockDurationsString.toInt();
        numBlocks++;
        debugOut(String("BD[")+numBlocks+"] = "+blockDurationsString.toInt());
        int i = blockDurationsString.indexOf(',');
        if (i>-1) {
          blockDurationsString = blockDurationsString.substring(i+1);
          blockDurationsString.trim();
        } else {
          break;
        }
      } // while
    } else {
      // unknown parameter
      errorOut(String("Unknown Parameter: \"")+pName+"\"");
    }
  } else {
    // unexpected input
    errorOut(String("Unexpected Input: \"")+input+"\"");
  }
}

void temperatureControl() {
  float temp1, temp2;
  // check temperature
  temp1 = checkTMP(TMP1_PIN);
  if (parameters.tmp2_active){
    temp2 = checkTMP(TMP2_PIN);
  }
  // turn heater ON/Off
  if (temp1 <= parameters.targetTemp && temp1 > 0) { // if (temp1 > 0) then we don't trust sensor
    digitalWrite(RELAY_PIN, HIGH);
  } else{
    digitalWrite(RELAY_PIN, LOW);
  }
}

float checkTMP(int tmp_pin){
  int tmpRead = analogRead(tmp_pin);         //Read output from TMP36
  float volts = 3.3*tmpRead/1023;          //Convert to volts from 10 bit
  float degC = (volts - .75)/.01 + 25;     //Convert to Celcius(1C/10mV, 750mV@25C)
  return degC;
}


void turnToneOn() {
  toneOn = true;
  tone(SPEAKER_PIN, parameters.fcToneFrequency);
  noTone(DUMMYTONE_PIN);
  debugOut("TONE ON");
  logData(String("Tone"), 1);
}
void turnToneOff() {
  toneOn = false;
  noTone(SPEAKER_PIN);
  digitalWrite(SPEAKER_PIN, LOW);
  tone(DUMMYTONE_PIN, 5);
  debugOut("TONE OFF");
  logData(String("Tone"), 0);
}
void turnShockOn() {
  shockOn = true;
  digitalWrite(SHOCK_PIN, HIGH);
  debugOut("SHOCK ON");
  logData(String("Shock"), 1);
}
void turnShockOff() {
  shockOn = false;
  digitalWrite(SHOCK_PIN, LOW);
  debugOut("SHOCK OFF");
  logData(String("Shock"), 0);
}


void setup(){

  // set pin modes
  pinMode(TMP1_PIN, INPUT);
  pinMode(TMP2_PIN, INPUT);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(ONBOARDLED_PIN, OUTPUT);  // for debugging
  pinMode(BUTTON1_PIN, INPUT_PULLUP);
  pinMode(BUTTON2_PIN, INPUT_PULLUP);
  pinMode(SPEAKER_PIN, OUTPUT);
  pinMode(SHOCK_PIN, OUTPUT);
  pinMode(DUMMYTONE_PIN, OUTPUT);
  pinMode(NOSEPOKE_PIN, INPUT);
  pinMode(SOLENOID_PIN, OUTPUT);

  pinMode(IR1_PIN, OUTPUT);
  pinMode(IR2_PIN, OUTPUT);
  pinMode(IR3_PIN, OUTPUT);
  pinMode(IR4_PIN, OUTPUT);

  //Open serial communication
  Serial.begin(9600);

  // set up first temperature check
  nextTempTime = millis()+parameters.tempPeriod;
  nextTempLogTime = millis()+parameters.tempLogPeriod;

  // don't start off in a fear conditioning protocol
  inFearConditioningMode = false;

  // initialize parameters to default values
  initParams();
}

// //debug
// int loopCounter =0;

void loop(){

  // 1)  Deal with Serial input
  readAndInterpretAvailableChars();

  // 2) Deal with temperature
  if (millis() >= nextTempTime) {
    // run temperature control
    temperatureControl();
    nextTempTime = millis()+parameters.tempPeriod;
  }
  if (millis() >= nextTempLogTime) {
    // log temperature
    logData("Temp",  checkTMP(TMP1_PIN));
    nextTempLogTime = millis()+parameters.tempLogPeriod;
  }

  // 3) Deal with conditioning logic
  if (inFearConditioningMode) {
    if (!shockOn && millis() >= startFCShockTime) {
      turnShockOn();
    }
    if (!toneOn && millis() >= startFCToneTime) {
      turnToneOn();
    }
    if (millis() >= endFCBlockTime) {
      currentFCBlockIndex++;
      runFCBlock(currentFCBlockIndex);
    }
  }

  // 4) Deal with nosepoke

  // Open solenoid when nose poke is triggered
  if (nosepokeOnStandby && digitalRead(NOSEPOKE_PIN) == HIGH){
    // Update counter, booleans, and solenoidClosingTime
    nosepokeOnStandby = false;
    solenoidOpen = true;
    nosepokeCount++;
    solenoidClosingTime = millis() + parameters.dispensationInterval;
    // Open Solenoid
    digitalWrite(SOLENOID_PIN, HIGH);
    debugOut("NOSE POKE TRIGGERED");
    logData(String("Nose"), nosepokeCount);
    logData(String("Water"), waterDeliveryCount);
  }

  // Close solenoid when interval is reached
  if (solenoidOpen && millis() >= solenoidClosingTime){
    digitalWrite(SOLENOID_PIN, LOW);
    solenoidOpen = false;
  }

  // Set nosepoke to standby when solenoid is closed and beam reconnets
  if (!nosepokeOnStandby && !solenoidOpen && digitalRead(NOSEPOKE_PIN) == LOW){
    nosepokeOnStandby = true;
  }

 delayMicroseconds(1000);

  // // debug
  // loopCounter++;
  // if ((loopCounter%10000)==0) {
  //   debugOut(".");
  // }

}
