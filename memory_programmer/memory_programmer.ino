// Uncomment the next line to perform all read/write operations
// in a memory buffer instead of on a hardware EEPROM.
// #define TEST_ENABLED 1

#define CHIP_ENABLE_PIN 23
#define OUTPUT_ENABLE_PIN 25
#define WRITE_ENABLE_PIN 27

#define ADDR_PORT_SIZE 11
#define ADDR_MAX (1 << ADDR_PORT_SIZE)
// The pins should be in increasing order. (A0 ... A10)
static const int addr_port[ADDR_PORT_SIZE] = { 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 32 };

// Define data pins.
#define DATA_PORT_SIZE 8
// D0 ... D7
static const int data_port[DATA_PORT_SIZE] = { 46, 47, 48, 49, 50, 51, 52, 53 };

#define COMMAND_NONE 0
#define COMMAND_SEEK 0x10
#define COMMAND_READ 0x20
#define COMMAND_WRITE 0x40

#define RESPONSE_SUCCESS 0xA5
#define RESPONSE_ERROR 0xB7

// Memory interface.
static unsigned short memoryAddress;

void memoryInit();
void memorySetAddress();
byte memoryReadByte();
void memoryWriteByte(byte data);

#if TEST_ENABLED
static byte testMemory[256];
#endif

void setup() {
  memoryAddress = 0;

  Serial.begin(9600);
  while (!Serial)
    ;

  memoryInit();
}

void loop() {
  static int lastReceivedByte;
  static int receivedByte = 0;

  static int command = COMMAND_NONE;
  static int checksum;
  static int payloadIndex;
  static int response;

  static bool isCommandDone = false;
  static bool isCommandSuccess = false;
  static bool commandHasResponse = false;

  static unsigned short newMemoryAddress;
  static unsigned char newData;

  if (Serial.available() > 0) {
    lastReceivedByte = receivedByte;
    receivedByte = Serial.read();

    if (receivedByte != -1) {
      receivedByte &= 0xFF;

      switch (command) {
        case COMMAND_NONE:
          if (lastReceivedByte == ((~receivedByte) & 0xFF) && (lastReceivedByte == COMMAND_SEEK || lastReceivedByte == COMMAND_READ || lastReceivedByte == COMMAND_WRITE)) {
            command = lastReceivedByte;

            checksum = lastReceivedByte + receivedByte;
            payloadIndex = 0;

            newMemoryAddress = 0;
            newData = 0;
          }
          break;
        case COMMAND_SEEK:
          if (payloadIndex < 2) {
            newMemoryAddress <<= 8;
            newMemoryAddress |= receivedByte;
            checksum += receivedByte;
          } else {
            isCommandDone = true;
            isCommandSuccess = (checksum & 0xFF) == receivedByte && newMemoryAddress < ADDR_MAX;

            if (isCommandSuccess) {
              memoryAddress = newMemoryAddress;
            }
          }
          payloadIndex++;
          break;
        case COMMAND_READ:
          isCommandDone = true;
          commandHasResponse = true;
          isCommandSuccess = (checksum & 0xFF) == receivedByte;

          if (isCommandSuccess) {
#if TEST_ENABLED
            response = testMemory[memoryAddress];
#else
            response = memoryReadByte();
#endif
            // Auto-increment memory address on successful read.
            memoryAddress++;
          }
          break;
        case COMMAND_WRITE:
          if (payloadIndex < 1) {
            newData = receivedByte;
            checksum += receivedByte;
          } else {
            isCommandDone = true;
            isCommandSuccess = (checksum & 0xFF) == receivedByte;

            if (isCommandSuccess) {
#if TEST_ENABLED
              testMemory[memoryAddress] = newData;
#else
              memoryWriteByte(newData);
#endif

              // Auto-increment memory address on successful write.
              memoryAddress++;
            }
          }
          payloadIndex++;
          break;
      }

      if (isCommandDone) {
        if (isCommandSuccess) {
          Serial.write(RESPONSE_SUCCESS);
          Serial.write((~RESPONSE_SUCCESS) & 0xFF);

          if (commandHasResponse) {
            checksum = RESPONSE_SUCCESS + ((~RESPONSE_SUCCESS) & 0xFF) + response;
            checksum &= 0xFF;

            Serial.write(response);
            Serial.write(checksum);
          }
        } else {
          Serial.write(RESPONSE_ERROR);
          Serial.write((~RESPONSE_ERROR) & 0xFF);
        }

        isCommandDone = false;
        commandHasResponse = false;
        isCommandSuccess = false;
        command = COMMAND_NONE;
      }
    }
  }
}

void memoryInit() {
  digitalWrite(OUTPUT_ENABLE_PIN, HIGH);
  digitalWrite(CHIP_ENABLE_PIN, HIGH);
  digitalWrite(WRITE_ENABLE_PIN, HIGH);

  pinMode(CHIP_ENABLE_PIN, OUTPUT);
  pinMode(OUTPUT_ENABLE_PIN, OUTPUT);
  pinMode(WRITE_ENABLE_PIN, OUTPUT);

  for (int i = 0; i < ADDR_PORT_SIZE; i++) {
    pinMode(addr_port[i], OUTPUT);
  }

#if TEST_ENABLED
  for (int i = 0; i < 256; i++) {
    testMemory[i] = 0xFF;
  }
#endif
}

void memorySetAddress() {
  for (int i = 0; i < ADDR_PORT_SIZE; i++) {
    digitalWrite(addr_port[i], (memoryAddress & (0x0001 << i)) != 0);
  }
}

byte memoryReadByte() {
  byte data = 0x00;

  digitalWrite(OUTPUT_ENABLE_PIN, HIGH);

  for (int i = 0; i < DATA_PORT_SIZE; i++) {
    pinMode(data_port[i], INPUT);
  }

  memorySetAddress();

  digitalWrite(CHIP_ENABLE_PIN, LOW);
  digitalWrite(OUTPUT_ENABLE_PIN, LOW);

  for (int i = DATA_PORT_SIZE - 1; i >= 0; i--) {
    data <<= 1;
    data |= digitalRead(data_port[i]);
  }

  digitalWrite(OUTPUT_ENABLE_PIN, LOW);
  digitalWrite(CHIP_ENABLE_PIN, LOW);

  return data;
}

void memoryWriteByte(byte data) {
  digitalWrite(OUTPUT_ENABLE_PIN, HIGH);
  digitalWrite(CHIP_ENABLE_PIN, LOW);

  memorySetAddress();

  for (int i = 0; i < DATA_PORT_SIZE; i++) {
    pinMode(data_port[i], OUTPUT);
  }

  for (int i = DATA_PORT_SIZE - 1; i >= 0; i--) {
    digitalWrite(data_port[i], ((data >> i) & 0x01));
  }

  digitalWrite(WRITE_ENABLE_PIN, LOW);
  delayMicroseconds(1);
  digitalWrite(WRITE_ENABLE_PIN, HIGH);
  delay(1);

  digitalWrite(CHIP_ENABLE_PIN, HIGH);
}
