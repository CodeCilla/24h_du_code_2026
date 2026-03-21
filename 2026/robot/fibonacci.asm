; ============================================================================
; FIBONACCI OPTIMISÉ - Affiche tous les termes de Fibonacci de 0 à 255
; ============================================================================
;
; PRINCIPE DE L'OPTIMISATION :
; ---------------------------
; Problème du code original : L'addition était simulée par une boucle qui
; incrémente R1, R0 fois. Pour calculer 144+89, cela faisait 89 itérations !
; → Complexité O(n) par addition, expliquant les ~4000 cycles totaux.
;
; Solution mathématique (Complément à 256 sur 8 bits) :
; ---------------------------------------------------
; Comme il n'y a pas d'instruction ADD, on utilise la formule :
;                    a + b = 0 - (0 - a - b)
;
; Explication : Sur 8 bits, les nombres négatifs sont codés ainsi :
;   -x ≡ 256 - x (mod 256)
;   
; Donc :
;   0 - b = -b (mod 256)          [ex: 0-3 = 253 qui représente -3]
;   -b - a = -(a+b) (mod 256)     [ex: 253-5 = 248 qui représente -8]
;   0 - (-(a+b)) = a+b (mod 256)  [ex: 0-248 = 8 qui représente +8]
;
; Avantages :
;   • Addition en O(1) : toujours 4 instructions, quelles que soient les valeurs
;   • Pas d'utilisation de la pile (PUSH/POP/CALL supprimés)
;   • Registres uniquement : R0, R1, R2, R3
;   • ~12 cycles par itération au lieu de 300-400
;   • Total : ~170-180 cycles au lieu de 4000 (x23 plus rapide)
;
; REGISTRES UTILISÉS :
; ------------------
; R0 = a (terme courant, ex: 0, 1, 1, 2, 3, 5, 8...)
; R1 = b (terme suivant, ex: 1, 1, 2, 3, 5, 8, 13...)
; R2 = registre temporaire pour le calcul -(a+b)
; R3 = constante 0 (optimisation pour éviter MOV Rx 0 répétés)
;
; DÉTECTION DE DÉPASSEMENT (Overflow 8 bits) :
; ------------------------------------------
; Quand a+b > 255, le résultat tronqué sur 8 bits devient < a (car overflow).
; Ex: 233 + 144 = 377 → 377-256 = 121, et 121 < 233.
; Donc si nouveau_b < nouveau_a, on arrête (on a dépassé 255).
;
; ============================================================================

_main:
    MOV R0 0        ; a = 0 (premier terme)
    MOV R1 1        ; b = 1 (deuxième terme)
    MOV R3 0        ; R3 = constante 0 (pour les calculs)

_loop:
    OUT R0          ; afficher terme courant (1 cycle)
    
    ; --- Calcul de -(a+b) dans R2 en O(1) (4 instructions) ---
    MOV R2 R3       ; R2 = 0 (1 cycle)
    SUB R2 R1       ; R2 = 0 - b = -b (1 cycle)
    SUB R2 R0       ; R2 = -b - a = -(a+b) (1 cycle)
    
    ; --- Mise à jour : a=b, b=a+b ---
    MOV R0 R1       ; a = ancien b (1 cycle)
    MOV R1 R3       ; R1 = 0 (1 cycle)
    SUB R1 R2       ; b = 0 - (-(a+b)) = a+b (1 cycle)
    
    ; --- Vérification dépassement ---
    CMP R1 R0       ; comparer nouveau b avec nouveau a (1 cycle)
    JLT _done       ; si b < a : overflow détecté, c'est fini (2 cycles)
    JMP _loop       ; sinon continuer la séquence (2 cycles)

_done:
    OUT R0          ; afficher le dernier terme valide (233)
    RET             ; fin du programme (pile vide)