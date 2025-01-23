// Motion control enemy 
// Features: 
// Added pwm servo drivers
// Disable skill button
// Weapon atk motion
// Can't atk while blocking

#include <Adafruit_PWMServoDriver.h>
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define skill_pin 12
#define Atk_button 11
#define run_pin 10
#define heal_pin 8
#define block_pin 9

#define SERVO_PUNGGUNG 0
#define SERVO_BAHUKANAN 1
#define SERVO_TANGANKIRI 2
#define SERVO_SIKUKANAN 3
#define SERVO_PINGGANG 4
#define SERVO_KAKIKANAN 5
#define SERVO_KAKIKIRI 6

// Character stats:
int damage = 0;
int hp = 30;
int deff = 800;
int atk = 300;
int enrgy = 30;
int maxenrgy = 30;
float critRate = 0.2; // Crit rate 20%
float critDMG = 1.0; // Crit DMG 100% (default duration * 1.0)

// Attack button
int button_state = 0;
unsigned long lastAtkTime = 0, atkInterval = 500;  // Attack timing
bool isAttacking = false;

// Skill button
int skill_press_count = 0;
int skill_state = 0;
int prev_skill_state = 0;

static bool isUsingSkill = false; // Status penggunaan skill
static unsigned long lastSkillTime = 0; // Waktu terakhir skill digunakan
static unsigned long skillAnimationStartTime = 0; // Waktu mulai animasi skill
const unsigned long skillCooldown = 5000; // Cooldown 5 detik
const unsigned long skillAnimationDuration = 300; // Durasi animasi skill (300 ms)

// Block button
int block_press_count = 0;
int block_state = 0;
int prev_block_state = 0;
unsigned long lastBlockTime = 0, blockInterval = 3000; // Block timing
bool isBlocking = false;

// Heal button
int heal_press_count = 0;
int heal_state = 0;
int prev_heal_state = 0;

// Energy management
unsigned long lastEnergyRegenTime = 0;
const unsigned long energyRegenInterval = 5000; // Regenerate 10 energy every 5 seconds
const int energyCostPerAttack = 10;

void setup()
{
  Serial.begin(9600);
  pinMode(heal_pin, INPUT_PULLUP);
  pinMode(block_pin, INPUT_PULLUP);
  pinMode(Atk_button, INPUT_PULLUP);
  pinMode(skill_pin, INPUT_PULLUP);
  pinMode(run_pin, INPUT);

  pwm.begin();
  pwm.setPWMFreq(50);

  setIdlePosition();
  Serial.println("Start...");
  setServoAngle(SERVO_SIKUKANAN, 100);;//-kanan +kiri
}

void setServoAngle(int channel, int angle)
{
  int pulseLength = map(angle, 0, 180, 102, 512); // Map angle to pulse length
  pwm.setPWM(channel, 0, pulseLength);
}

void setIdlePosition()
{
  setServoAngle(SERVO_BAHUKANAN, 100);//-kanan +kiri
  setServoAngle(SERVO_TANGANKIRI, 140);//+kiri -kanan
  setServoAngle(SERVO_PUNGGUNG, 110);//+turun -naik
  setServoAngle(SERVO_SIKUKANAN, 100);;//-kanan +kiri
  setServoAngle(SERVO_PINGGANG, 70);//-kanan +kiri
}

bool debounceButton(int pin) {
  static unsigned long lastDebounceTime = 0;
  static int lastButtonState = LOW;
  int currentState = digitalRead(pin);

  if (currentState != lastButtonState) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > 50) {  // Debounce 50ms
    if (currentState != button_state) {
      button_state = currentState;
    }
  }

  lastButtonState = currentState;
  return button_state == HIGH;
}

void BlockState() //Blocking menggunakan millis
{
  block_state = digitalRead(block_pin);
  
  if (block_state ==  LOW && !isBlocking) {
    isBlocking = true;
    lastBlockTime = millis();
    Serial.println("Blocking started...");
  }

  if (isBlocking) {
    unsigned long currentTime = millis();
    isBlockingActive = true;
    isBlocking = true;
    if (currentTime - lastBlockTime < 1000) {
      setServoAngle(SERVO_TANGANKIRI, 100);
      setServoAngle(SERVO_PINGGANG, 60);
      setServoAngle(SERVO_BAHUKANAN, 100);//-kanan +kiri
      setServoAngle(SERVO_PUNGGUNG, 110);//+turun -naik
      delay(50);
    } else {
      isBlocking = false;
      setIdlePosition();
      Serial.println("Blocking ended.");
    }
  }
}

void handleAtkState() {
  static int animationIndex = 0;  // Indeks untuk memilih animasi
  button_state = debounceButton(Atk_button);

  if (isBlocking) {
    Serial.println("Cannot attack while blocking.");
    return;  // Langsung keluar dari fungsi jika blocking aktif
  }

  // Check energy level before attacking
  if (button_state == LOW && !isAttacking) {
    if (enrgy >= energyCostPerAttack) {
      isAttacking = true;
      lastAtkTime = millis();
      enrgy -= energyCostPerAttack;  // Deduct energy
      Serial.print("Attack started. Energy left: ");
      Serial.println(enrgy);
    } else {
      Serial.println("Low energy, wait 5s!");
    }
  }

  if (isAttacking) {
    unsigned long currentTime = millis();

    switch (animationIndex) {
      case 0:  // Animasi serangan 1
        if (currentTime - lastAtkTime < 200) {
          setServoAngle(SERVO_BAHUKANAN, 180);
          setServoAngle(SERVO_PINGGANG, 160);
          setServoAngle(SERVO_PUNGGUNG, 40);
          setServoAngle(SERVO_BAHUKANAN, 180);
        } else if (currentTime - lastAtkTime < 800) {
          setServoAngle(SERVO_PINGGANG, 40);
          setServoAngle(SERVO_PUNGGUNG, 80);
          setServoAngle(SERVO_BAHUKANAN, 100);//-kanan +kiri
        } else {
          isAttacking = false;
          animationIndex = (animationIndex + 1) % 3;  // Pindah ke animasi berikutnya
          setIdlePosition();
          Serial.println("Attack 1 ended.");
        }
        break;

      case 1:  // Animasi serangan 2
        if (currentTime - lastAtkTime < 300) {
          setServoAngle(SERVO_BAHUKANAN, 180);
          setServoAngle(SERVO_PUNGGUNG, 90);
          setServoAngle(SERVO_PINGGANG, 160);
        } else if (currentTime - lastAtkTime < 800) {
          setServoAngle(SERVO_PINGGANG, 60);
          setServoAngle(SERVO_BAHUKANAN, 100);//-kanan +kiri
        } else {
          isAttacking = false;
          animationIndex = (animationIndex + 1) % 3;  // Pindah ke animasi berikutnya
          setIdlePosition();
          Serial.println("Attack 2 ended.");
        }
        break;

      case 2:  // Animasi serangan 3
        if (currentTime - lastAtkTime < 250) {

         setServoAngle(SERVO_PINGGANG, 40);
         setServoAngle(SERVO_SIKUKANAN, 140);;//-kanan +kiri
        } else if (currentTime - lastAtkTime < 600) {

          setServoAngle(SERVO_PINGGANG, 140);
          setServoAngle(SERVO_PUNGGUNG, 80);
          setServoAngle(SERVO_BAHUKANAN, 160);
          setServoAngle(SERVO_SIKUKANAN, 100);;//-kanan +kiri
        } else {
          isAttacking = false;
          animationIndex = (animationIndex + 1) % 3;  // Pindah ke animasi berikutnya
          setIdlePosition();
          Serial.println("Attack 3 ended.");
        }
        break;
    }
  }
  else {
    // Servo dalam posisi idle saat tidak menyerang
    setIdlePosition();
  }
}
void regenerateEnergy() {
  unsigned long currentTime = millis();
  if (currentTime - lastEnergyRegenTime >= energyRegenInterval) {
    if (enrgy < maxenrgy) {
      enrgy = min(enrgy + 10, maxenrgy);  // Regenerate 10 energy, not exceeding max energy
      Serial.print("Energy regenerated. Current energy: ");
      Serial.println(enrgy);
    }
    lastEnergyRegenTime = currentTime;
  }
}

void loop() {
  BlockState();
  regenerateEnergy();
  handleAtkState();
}
