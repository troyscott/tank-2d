import pygame
import time

pygame.display.init()
pygame.font.init()

pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
print("Mixer settings:", pygame.mixer.get_init())
