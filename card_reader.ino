#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9
#define BUZZER_PIN 8
MFRC522 mfrc522(SS_PIN, RST_PIN);



void setup() {
	Serial.begin(115200);	// Initialize serial communications with the PC
	SPI.begin();			// Init SPI bus
	mfrc522.PCD_Init();	// Init MFRC522 card
	Serial.println("Scan PICC to see UID and type...");
  pinMode(BUZZER_PIN, OUTPUT);
  noTone(BUZZER_PIN);
}


void loop() {
	// Look for new cards
	if ( ! mfrc522.PICC_IsNewCardPresent()) {
		return;
	}

	// Select one of the cards
	if ( ! mfrc522.PICC_ReadCardSerial()) {
		return;
	}

	// Dump debug info about the card.
  // Way to check printed output for "Time out in communication?"
  //    to then ~not~ send data over and return a negative tone on the buzzer.
  
	mfrc522.PICC_DumpToSerial(&(mfrc522.uid));
    tone(BUZZER_PIN, 1000);
    delay(100);
    tone(BUZZER_PIN, 1300);
    delay(100);
    noTone(BUZZER_PIN);  
}
