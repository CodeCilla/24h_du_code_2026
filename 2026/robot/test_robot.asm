; Programme de test pour le robot AlphaBot (VM STLION)
; L'adresse mémoire 255 est utilisée pour contrôler les moteurs (Memory-Mapped I/O)
; Commandes: 1 = Avancer, 2 = Reculer, 3 = Gauche, 4 = Droite, 0 = Stop

; 1. Avancer pendant 1 seconde
MOV R0 1
MOV R1 0          ; R1 nous sert à avoir l'adresse base=0
STR R0 R1 255     ; Ecrit R0 (1) à l'adresse 255
TIM 137           ; Attendre 1 sec (137 = 128 + 9 -> bit7=1 => 100ms * (9+1) = 1000ms)

; 2. S'arrêter
MOV R0 0
STR R0 R1 255     ; Ecrit R0 (0) à l'adresse 255
RET
