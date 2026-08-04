#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GEOPOLITICA - Gioco di strategia mondiale nel terminale
Requisiti: Python 3.6+, pygame (per i suoni)
Installazione pygame: pip install pygame
"""

import os
import sys
import random
import time
import math
from collections import defaultdict

try:
    import pygame
    pygame.init()
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False
    print("Pygame non installato. I suoni saranno disabilitati.", file=sys.stderr)

# -------------------- UTILITY --------------------
def clear_screen():
    """Pulisce il terminale."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_center(text, width=80):
    """Stampa il testo centrato."""
    print(text.center(width))

def ansi_color(code, text):
    """Applica colore ANSI al testo."""
    return f"\033[{code}m{text}\033[0m"

# Colori
COLOR_RED = 31
COLOR_GREEN = 32
COLOR_YELLOW = 33
COLOR_BLUE = 34
COLOR_MAGENTA = 35
COLOR_CYAN = 36
COLOR_WHITE = 37
COLOR_BOLD = 1

# -------------------- SOUND MANAGER --------------------
class SoundManager:
    """Gestisce la riproduzione di suoni tramite Pygame."""
    def __init__(self):
        self.enabled = SOUND_AVAILABLE
        if self.enabled:
            # Genera suoni come onde sinusoidali
            self.sounds = {
                'click': self._generate_tone(800, 0.1, 0.3),
                'war': self._generate_tone(150, 0.8, 0.5),
                'peace': self._generate_tone(600, 0.5, 0.3),
                'attack': self._generate_tone(300, 0.3, 0.6),
                'event': self._generate_tone(1000, 0.2, 0.4),
                'build': self._generate_tone(1200, 0.15, 0.2),
                'error': self._generate_tone(200, 0.4, 0.5),
                'victory': self._generate_tone(880, 0.5, 0.7),
                'defeat': self._generate_tone(220, 1.0, 0.5),
            }

    def _generate_tone(self, frequency, duration, volume):
        """Genera un suono semplice (onda sinusoidale) come oggetto Sound."""
        if not self.enabled:
            return None
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        buffer = bytearray()
        for i in range(n_samples):
            value = int(volume * 32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
            buffer.extend(value.to_bytes(2, 'little', signed=True))
        return pygame.mixer.Sound(buffer)

    def play(self, sound_key):
        """Riproduce un suono per chiave."""
        if self.enabled and sound_key in self.sounds:
            self.sounds[sound_key].play()

# Istanza globale
sounds = SoundManager()

# -------------------- COUNTRY CLASS --------------------
class Country:
    """Rappresenta una nazione con attributi e metodi."""
    def __init__(self, name, pop, gdp, military, treasury, approval, color_code=COLOR_WHITE):
        self.name = name
        self.population = pop          # in milioni
        self.gdp = gdp                # in miliardi
        self.military = military       # punteggio militare (0-100)
        self.treasury = treasury       # in miliardi
        self.approval = approval       # 0-100
        self.color = color_code
        self.allies = []              # lista di nomi di paesi alleati
        self.at_war = []              # lista di nomi di paesi nemici
        self.trade_partners = []      # lista di nomi
        self.infrastructure = 50       # 0-100
        self.tech_level = 30
        self.units = {'army': 10, 'navy': 5, 'air': 3}
        self.tax_rate = 20            # percentuale
        self.defeated = False
        self.controlled_territories = [name]  # lista di nomi (per espansione)

    def total_power(self):
        """Calcola il potere totale del paese (per AI e classifiche)."""
        return (self.military * 0.4 +
                self.gdp * 0.3 +
                self.population * 0.1 +
                self.infrastructure * 0.1 +
                self.tech_level * 0.1)

    def income(self):
        """Calcola l'income annuale (in miliardi)."""
        base = self.gdp * 0.05
        tax_income = base * (self.tax_rate / 100)
        # Bonus da alleati commerciali
        trade_bonus = len(self.trade_partners) * 2
        return tax_income + trade_bonus

    def expenses(self):
        """Spese annuali (militare, infrastruttura, etc.)."""
        military_spend = self.military * 0.2
        infra_spend = self.infrastructure * 0.1
        return military_spend + infra_spend + 5

    def net_income(self):
        return self.income() - self.expenses()

    def update(self):
        """Aggiorna lo stato del paese (popolazione, tesoro, ecc.)."""
        if self.defeated:
            return
        # Crescita popolazione
        growth = random.uniform(-0.005, 0.015)
        self.population = max(1, self.population * (1 + growth))
        # Cambio approvazione basato su economia e tassazione
        approval_change = 0
        if self.tax_rate > 40:
            approval_change -= 2
        elif self.tax_rate < 15:
            approval_change += 1
        if self.net_income() > 10:
            approval_change += 1
        elif self.net_income() < -5:
            approval_change -= 2
        # Eventi casuali possono modificare
        self.approval = max(0, min(100, self.approval + approval_change + random.uniform(-1, 1)))
        # Tesoro
        self.treasury += self.net_income()
        # Se tesoro negativo, penalità
        if self.treasury < -20:
            self.approval -= 3
            self.military *= 0.98

    def __str__(self):
        status = "VIVO" if not self.defeated else "SOTTOMESSO"
        return f"{self.name} (Potenza: {self.total_power():.1f}) - {status}"

# -------------------- GAME CLASS --------------------
class Game:
    """Gestisce lo stato globale del gioco, turni, IA, eventi."""
    def __init__(self):
        self.countries = {}          # dict {name: Country}
        self.player_country = None
        self.turn = 0
        self.running = True
        self.events_log = []
        self.game_over = False
        self.winner = None

        self._init_countries()
        self._init_player()

    def _init_countries(self):
        """Crea le nazioni predefinite."""
        # (nome, popolazione, gdp, militare, tesoro, approvazione, colore)
        data = [
            ("USA", 331, 23000, 85, 500, 60, COLOR_BLUE),
            ("Cina", 1440, 18000, 80, 400, 70, COLOR_RED),
            ("Russia", 146, 1700, 75, 200, 55, COLOR_YELLOW),
            ("India", 1400, 3500, 65, 150, 65, COLOR_GREEN),
            ("Regno Unito", 67, 3100, 60, 180, 58, COLOR_MAGENTA),
            ("Francia", 65, 2900, 55, 170, 62, COLOR_CYAN),
            ("Germania", 83, 4200, 50, 250, 60, COLOR_WHITE),
            ("Brasile", 213, 1800, 40, 90, 50, COLOR_YELLOW),
            ("Giappone", 126, 5000, 45, 300, 55, COLOR_WHITE),
            ("Australia", 25, 1500, 30, 100, 65, COLOR_GREEN),
        ]
        for name, pop, gdp, mil, tres, app, col in data:
            self.countries[name] = Country(name, pop, gdp, mil, tres, app, col)

    def _init_player(self):
        """Chiede al giocatore di selezionare una nazione."""
        clear_screen()
        print_center("=== GEOPOLITICA ===")
        print("\nScegli la tua nazione:\n")
        names = list(self.countries.keys())
        for i, name in enumerate(names, 1):
            c = self.countries[name]
            print(f"{i}. {name} (Pop: {c.population:.0f}M, PIL: {c.gdp}B, Potenza: {c.total_power():.1f})")
        while True:
            try:
                choice = int(input("\nInserisci il numero: "))
                if 1 <= choice <= len(names):
                    self.player_country = self.countries[names[choice-1]]
                    break
                else:
                    print("Scelta non valida.")
            except ValueError:
                print("Inserisci un numero.")

        print(f"\nHai scelto {self.player_country.name}!")
        sounds.play('click')
        time.sleep(1)

    def save_game(self, filename="savegame.json"):
        """Salva lo stato su file JSON."""
        import json
        # Semplificato: non implementato per brevità
        pass

    def load_game(self, filename="savegame.json"):
        """Carica lo stato da file."""
        pass

    def display_map(self):
        """Mostra una mappa ASCII con i paesi e i loro status."""
        clear_screen()
        print_center("=== MAPPA MONDIALE ===")
        print("\nLegenda: [Nome] Potenza: X.X | alleati, nemici\n")
        # Dividiamo in righe per una migliore visualizzazione
        items = list(self.countries.items())
        # Ordina per potenza
        items.sort(key=lambda x: x[1].total_power(), reverse=True)
        for i, (name, c) in enumerate(items, 1):
            status = "VIVO" if not c.defeated else "SOTTOMESSO"
            color = c.color
            power = c.total_power()
            allies = ", ".join(c.allies) if c.allies else "nessuno"
            enemies = ", ".join(c.at_war) if c.at_war else "nessuno"
            print(f"{i:2}. {ansi_color(color, name)} (Potenza: {power:5.1f}) {status}")
            print(f"    Pop: {c.population:6.0f}M  PIL: {c.gdp:5.0f}B  Tesoro: {c.treasury:6.1f}B  Approv: {c.approval:3.0f}%")
            print(f"    Alleati: {allies}  Nemici: {enemies}")
            print(f"    Esercito: {c.units['army']}  Marina: {c.units['navy']}  Aviazione: {c.units['air']}")
            print()

    def display_stats(self):
        """Mostra statistiche dettagliate del paese giocatore."""
        c = self.player_country
        clear_screen()
        print_center(f"=== STATISTICHE DI {c.name.upper()} ===")
        print(f"Popolazione: {c.population:.1f} milioni")
        print(f"PIL: {c.gdp:.1f} miliardi")
        print(f"Tesoro: {c.treasury:.1f} miliardi")
        print(f"Potenza militare: {c.military:.1f}")
        print(f"Approvazione: {c.approval:.1f}%")
        print(f"Infrastrutture: {c.infrastructure:.1f}")
        print(f"Livello tecnologico: {c.tech_level:.1f}")
        print(f"Tassazione: {c.tax_rate:.1f}%")
        print(f"Entrate nette annuali: {c.net_income():.1f} miliardi")
        print(f"Unità: Esercito {c.units['army']}, Marina {c.units['navy']}, Aviazione {c.units['air']}")
        print(f"Alleati: {', '.join(c.allies) if c.allies else 'nessuno'}")
        print(f"Nemici: {', '.join(c.at_war) if c.at_war else 'nessuno'}")
        print()

    def player_turn(self):
        """Gestisce il turno del giocatore."""
        c = self.player_country
        if c.defeated:
            print("Sei stato sconfitto! Game Over.")
            self.game_over = True
            return

        while True:
            self.display_stats()
            print("Azioni disponibili:")
            print("1. Gestione economia")
            print("2. Gestione militare")
            print("3. Diplomazia")
            print("4. Visualizza mappa")
            print("5. Termina turno")
            print("6. Salva e esci")
            choice = input("Scegli: ")
            if choice == '1':
                self.economy_menu()
            elif choice == '2':
                self.military_menu()
            elif choice == '3':
                self.diplomacy_menu()
            elif choice == '4':
                self.display_map()
                input("Premi Invio per continuare...")
            elif choice == '5':
                break
            elif choice == '6':
                self.save_game()
                self.running = False
                break
            else:
                print("Scelta non valida.")

        # Aggiorna il paese dopo le azioni
        c.update()

    def economy_menu(self):
        """Sottomenu per gestire economia e tassazione."""
        c = self.player_country
        clear_screen()
        print_center("=== GESTIONE ECONOMIA ===")
        print(f"Tassazione attuale: {c.tax_rate}%")
        print(f"Tesoro: {c.treasury:.1f} miliardi")
        print("1. Modifica tassazione")
        print("2. Investi in infrastrutture (costo 20B)")
        print("3. Investi in tecnologia (costo 15B)")
        print("4. Ritorna")
        choice = input("Scegli: ")
        if choice == '1':
            try:
                new_rate = float(input("Nuova aliquota (0-100): "))
                if 0 <= new_rate <= 100:
                    c.tax_rate = new_rate
                    sounds.play('click')
                else:
                    print("Valore fuori intervallo.")
            except ValueError:
                print("Numero non valido.")
        elif choice == '2':
            if c.treasury >= 20:
                c.treasury -= 20
                c.infrastructure = min(100, c.infrastructure + 10)
                sounds.play('build')
                print("Infrastrutture migliorate.")
            else:
                sounds.play('error')
                print("Tesoro insufficiente.")
        elif choice == '3':
            if c.treasury >= 15:
                c.treasury -= 15
                c.tech_level = min(100, c.tech_level + 8)
                sounds.play('build')
                print("Tecnologia avanzata.")
            else:
                sounds.play('error')
                print("Tesoro insufficiente.")
        else:
            return
        input("Premi Invio per continuare...")

    def military_menu(self):
        """Sottomenu per azioni militari."""
        c = self.player_country
        clear_screen()
        print_center("=== GESTIONE MILITARE ===")
        print(f"Potenza militare: {c.military:.1f}")
        print(f"Unità: Esercito {c.units['army']}, Marina {c.units['navy']}, Aviazione {c.units['air']}")
        print("1. Recluta esercito (costo 10B, +2 esercito)")
        print("2. Costruisci navi (costo 12B, +2 marina)")
        print("3. Costruisci aerei (costo 8B, +2 aviazione)")
        print("4. Attacca un paese")
        print("5. Ritorna")
        choice = input("Scegli: ")
        if choice == '1':
            if c.treasury >= 10:
                c.treasury -= 10
                c.units['army'] += 2
                c.military += 2
                sounds.play('build')
                print("Nuovo esercito reclutato.")
            else:
                sounds.play('error')
                print("Tesoro insufficiente.")
        elif choice == '2':
            if c.treasury >= 12:
                c.treasury -= 12
                c.units['navy'] += 2
                c.military += 2
                sounds.play('build')
                print("Nuove navi costruite.")
            else:
                sounds.play('error')
                print("Tesoro insufficiente.")
        elif choice == '3':
            if c.treasury >= 8:
                c.treasury -= 8
                c.units['air'] += 2
                c.military += 2
                sounds.play('build')
                print("Nuovi aerei costruiti.")
            else:
                sounds.play('error')
                print("Tesoro insufficiente.")
        elif choice == '4':
            self.attack_menu()
        else:
            return
        input("Premi Invio per continuare...")

    def attack_menu(self):
        """Scegli un nemico da attaccare."""
        c = self.player_country
        targets = [name for name, country in self.countries.items()
                   if not country.defeated and name != c.name and name not in c.allies]
        if not targets:
            print("Nessun bersaglio disponibile (tutti alleati o sconfitti).")
            return
        print("\nPaesi attaccabili:")
        for i, name in enumerate(targets, 1):
            t = self.countries[name]
            print(f"{i}. {name} (Potenza: {t.total_power():.1f})")
        try:
            choice = int(input("Scegli il numero: "))
            if 1 <= choice <= len(targets):
                target_name = targets[choice-1]
                self.declare_war(c.name, target_name)
                # Esegui combattimento
                self.battle(c.name, target_name)
            else:
                print("Scelta non valida.")
        except ValueError:
            print("Numero non valido.")

    def diplomacy_menu(self):
        """Sottomenu per azioni diplomatiche."""
        c = self.player_country
        clear_screen()
        print_center("=== DIPLOMAZIA ===")
        print("1. Proponi alleanza")
        print("2. Rompi alleanza")
        print("3. Dichiarazione di guerra")
        print("4. Offri pace")
        print("5. Proponi scambio commerciale")
        print("6. Ritorna")
        choice = input("Scegli: ")
        if choice == '1':
            self.propose_alliance()
        elif choice == '2':
            self.break_alliance()
        elif choice == '3':
            self.declare_war_menu()
        elif choice == '4':
            self.offer_peace()
        elif choice == '5':
            self.propose_trade()
        else:
            return
        input("Premi Invio per continuare...")

    def propose_alliance(self):
        """Propone alleanza a un altro paese."""
        c = self.player_country
        targets = [name for name, country in self.countries.items()
                   if not country.defeated and name != c.name and name not in c.allies]
        if not targets:
            print("Nessun potenziale alleato.")
            return
        print("\nPaesi disponibili:")
        for i, name in enumerate(targets, 1):
            t = self.countries[name]
            print(f"{i}. {name} (Potenza: {t.total_power():.1f})")
        try:
            choice = int(input("Scegli: "))
            if 1 <= choice <= len(targets):
                target = targets[choice-1]
                # L'IA decide in base a vari fattori
                if self._ai_diplomacy_accept(target, c.name):
                    c.allies.append(target)
                    self.countries[target].allies.append(c.name)
                    sounds.play('peace')
                    print(f"Alleanza stipulata con {target}!")
                else:
                    sounds.play('error')
                    print(f"{target} ha rifiutato l'alleanza.")
            else:
                print("Scelta non valida.")
        except ValueError:
            print("Numero non valido.")

    def _ai_diplomacy_accept(self, proposer, target):
        """Decide se l'IA accetta l'alleanza."""
        # Basato su potenza e minacce comuni
        p = self.countries[proposer]
        t = self.countries[target]
        # Se hanno un nemico comune, probabilità alta
        common_enemies = set(p.at_war) & set(t.at_war)
        if common_enemies:
            return random.random() < 0.8
        # Se il proposer è più potente, accetta più volentieri
        if p.total_power() > t.total_power() * 1.5:
            return random.random() < 0.7
        return random.random() < 0.3

    def break_alliance(self):
        """Rompe un'alleanza esistente."""
        c = self.player_country
        if not c.allies:
            print("Non hai alleanze.")
            return
        print("Alleati attuali:")
        for i, ally in enumerate(c.allies, 1):
            print(f"{i}. {ally}")
        try:
            choice = int(input("Scegli alleato da rimuovere: "))
            if 1 <= choice <= len(c.allies):
                ally = c.allies[choice-1]
                c.allies.remove(ally)
                self.countries[ally].allies.remove(c.name)
                sounds.play('error')
                print(f"Alleanza con {ally} rotta.")
            else:
                print("Scelta non valida.")
        except ValueError:
            print("Numero non valido.")

    def declare_war_menu(self):
        """Menu per dichiarare guerra."""
        c = self.player_country
        targets = [name for name, country in self.countries.items()
                   if not country.defeated and name != c.name and name not in c.allies]
        if not targets:
            print("Nessun bersaglio disponibile.")
            return
        print("\nPaesi contro cui dichiarare guerra:")
        for i, name in enumerate(targets, 1):
            t = self.countries[name]
            print(f"{i}. {name} (Potenza: {t.total_power():.1f})")
        try:
            choice = int(input("Scegli: "))
            if 1 <= choice <= len(targets):
                target = targets[choice-1]
                self.declare_war(c.name, target)
            else:
                print("Scelta non valida.")
        except ValueError:
            print("Numero non valido.")

    def declare_war(self, attacker, defender):
        """Dichiara guerra e aggiorna stati."""
        if attacker not in self.countries or defender not in self.countries:
            return
        a = self.countries[attacker]
        d = self.countries[defender]
        if defender in a.allies:
            print("Non puoi dichiarare guerra a un alleato!")
            return
        if attacker in d.allies:
            print("Non puoi dichiarare guerra a un alleato!")
            return
        # Aggiungi ai nemici
        if defender not in a.at_war:
            a.at_war.append(defender)
        if attacker not in d.at_war:
            d.at_war.append(attacker)
        # Se hanno alleati, coinvolgili
        for ally in a.allies[:]:
            if ally not in self.countries:
                continue
            ally_c = self.countries[ally]
            if defender not in ally_c.at_war:
                ally_c.at_war.append(defender)
                print(f"{ally} si unisce alla guerra a fianco di {attacker}!")
        for ally in d.allies[:]:
            if ally not in self.countries:
                continue
            ally_c = self.countries[ally]
            if attacker not in ally_c.at_war:
                ally_c.at_war.append(attacker)
                print(f"{ally} si unisce alla guerra a fianco di {defender}!")

        sounds.play('war')
        print(f"GUERRA dichiarata tra {attacker} e {defender}!")

    def offer_peace(self):
        """Offre la pace a un nemico."""
        c = self.player_country
        if not c.at_war:
            print("Non sei in guerra.")
            return
        print("Nemici attuali:")
        for i, enemy in enumerate(c.at_war, 1):
            print(f"{i}. {enemy}")
        try:
            choice = int(input("Scegli nemico a cui offrire pace: "))
            if 1 <= choice <= len(c.at_war):
                enemy = c.at_war[choice-1]
                # L'IA accetta se è in difficoltà
                enemy_c = self.countries[enemy]
                if enemy_c.total_power() < c.total_power() * 0.7 or enemy_c.treasury < 0:
                    # Accetta pace
                    c.at_war.remove(enemy)
                    enemy_c.at_war.remove(c.name)
                    sounds.play('peace')
                    print(f"Pace firmata con {enemy}.")
                else:
                    sounds.play('error')
                    print(f"{enemy} rifiuta la pace.")
            else:
                print("Scelta non valida.")
        except ValueError:
            print("Numero non valido.")

    def propose_trade(self):
        """Propone scambio commerciale."""
        c = self.player_country
        targets = [name for name, country in self.countries.items()
                   if not country.defeated and name != c.name and name not in c.trade_partners]
        if not targets:
            print("Nessun partner commerciale disponibile.")
            return
        print("\nPaesi per scambio:")
        for i, name in enumerate(targets, 1):
            t = self.countries[name]
            print(f"{i}. {name} (Potenza: {t.total_power():.1f})")
        try:
            choice = int(input("Scegli: "))
            if 1 <= choice <= len(targets):
                target = targets[choice-1]
                # L'IA accetta quasi sempre
                if random.random() < 0.7:
                    c.trade_partners.append(target)
                    self.countries[target].trade_partners.append(c.name)
                    sounds.play('click')
                    print(f"Accordo commerciale con {target}.")
                else:
                    sounds.play('error')
                    print(f"{target} rifiuta.")
            else:
                print("Scelta non valida.")
        except ValueError:
            print("Numero non valido.")

    def battle(self, attacker, defender):
        """Simula una battaglia tra due paesi."""
        a = self.countries[attacker]
        d = self.countries[defender]
        print(f"\n=== BATTAGLIA tra {attacker} e {defender} ===")
        # Calcola forze
        a_power = a.military * (1 + a.units['army'] * 0.1 + a.units['navy'] * 0.05 + a.units['air'] * 0.08)
        d_power = d.military * (1 + d.units['army'] * 0.1 + d.units['navy'] * 0.05 + d.units['air'] * 0.08)
        # Aggiungi bonus alleati
        for ally in a.allies:
            if ally in self.countries and not self.countries[ally].defeated:
                a_power += self.countries[ally].military * 0.2
        for ally in d.allies:
            if ally in self.countries and not self.countries[ally].defeated:
                d_power += self.countries[ally].military * 0.2

        # Fattore casuale
        a_power *= random.uniform(0.8, 1.2)
        d_power *= random.uniform(0.8, 1.2)

        print(f"Potenza attaccante: {a_power:.1f} vs difensore: {d_power:.1f}")
        sounds.play('attack')

        if a_power > d_power:
            print(f"{attacker} vince la battaglia!")
            # Danni al difensore
            d.military = max(0, d.military - 10)
            d.treasury -= 20
            d.approval -= 5
            # Perdita di territorio (simbolica)
            if len(d.controlled_territories) > 1:
                lost = d.controlled_territories.pop()
                a.controlled_territories.append(lost)
                print(f"{attacker} conquista {lost}!")
            # Se il difensore è troppo debole, viene sottomesso
            if d.military < 10 or d.treasury < -30 or d.approval < 10:
                d.defeated = True
                print(f"{defender} è stato sottomesso da {attacker}!")
                # Rimuovi da alleati e guerre
                for other in list(self.countries.values()):
                    if defender in other.allies:
                        other.allies.remove(defender)
                    if defender in other.at_war:
                        other.at_war.remove(defender)
                # Il vincitore ottiene bonus
                a.treasury += 30
                a.approval += 5
                sounds.play('victory')
            else:
                sounds.play('click')
        else:
            print(f"{defender} respinge l'attacco!")
            a.military = max(0, a.military - 8)
            a.treasury -= 15
            a.approval -= 3
            sounds.play('defeat')

        input("Premi Invio per continuare...")

    def ai_turn(self):
        """Esegue le azioni per tutti i paesi IA."""
        for name, c in self.countries.items():
            if c.defeated or name == self.player_country.name:
                continue
            # AI decisioni
            self._ai_manage_economy(c)
            self._ai_military(c)
            self._ai_diplomacy(c)
            c.update()

    def _ai_manage_economy(self, c):
        """IA gestisce tassazione e investimenti."""
        # Se tesoro basso, aumenta tasse
        if c.treasury < -10:
            c.tax_rate = min(50, c.tax_rate + 5)
        elif c.treasury > 50:
            c.tax_rate = max(10, c.tax_rate - 3)
        # Investi se ha surplus
        if c.treasury > 30 and c.infrastructure < 60:
            c.treasury -= 10
            c.infrastructure += 5
        if c.treasury > 25 and c.tech_level < 50:
            c.treasury -= 8
            c.tech_level += 4

    def _ai_military(self, c):
        """IA potenzia militare se minacciata."""
        # Costruisci unità se tesoro sufficiente
        if c.treasury > 20 and c.military < 70:
            if c.units['army'] < 20:
                c.treasury -= 10
                c.units['army'] += 2
                c.military += 2
        # Se in guerra, aumenta priorità
        if c.at_war:
            if c.treasury > 15 and c.units['navy'] < 15:
                c.treasury -= 12
                c.units['navy'] += 2
                c.military += 2
            if c.treasury > 10 and c.units['air'] < 10:
                c.treasury -= 8
                c.units['air'] += 2
                c.military += 2

    def _ai_diplomacy(self, c):
        """IA gestisce alleanze e guerre."""
        # Cerca alleanze se debole
        if c.total_power() < 50 and len(c.allies) < 2:
            potential = [name for name, country in self.countries.items()
                         if not country.defeated and name != c.name and name not in c.allies]
            if potential:
                target = random.choice(potential)
                if self._ai_diplomacy_accept(target, c.name):
                    c.allies.append(target)
                    self.countries[target].allies.append(c.name)
        # Se forte, attacca un vicino debole
        if c.total_power() > 80 and not c.at_war and len(c.at_war) == 0:
            weak = [name for name, country in self.countries.items()
                    if not country.defeated and name != c.name and name not in c.allies
                    and country.total_power() < c.total_power() * 0.6]
            if weak:
                target = random.choice(weak)
                self.declare_war(c.name, target)
                self.battle(c.name, target)

    def random_event(self):
        """Genera un evento casuale che influenza i paesi."""
        if random.random() > 0.3:  # 30% di probabilità per turno
            return
        event_type = random.choice(['disastro', 'boom', 'scoperta', 'rivolta'])
        affected = random.choice(list(self.countries.values()))
        if affected.defeated:
            return
        if event_type == 'disastro':
            damage = random.randint(5, 20)
            affected.treasury -= damage
            affected.population *= (1 - random.uniform(0.01, 0.05))
            affected.infrastructure = max(0, affected.infrastructure - 10)
            sounds.play('error')
            print(f"DISASTRO: {affected.name} subisce danni per {damage}B!")
        elif event_type == 'boom':
            gain = random.randint(10, 30)
            affected.treasury += gain
            affected.gdp *= (1 + random.uniform(0.02, 0.06))
            affected.approval = min(100, affected.approval + 5)
            sounds.play('event')
            print(f"BOOM ECONOMICO: {affected.name} guadagna {gain}B!")
        elif event_type == 'scoperta':
            affected.tech_level = min(100, affected.tech_level + 10)
            affected.gdp *= 1.05
            sounds.play('event')
            print(f"SCOPERTA TECNOLOGICA: {affected.name} avanza nella tecnologia!")
        elif event_type == 'rivolta':
            if affected.approval < 30:
                affected.treasury -= 15
                affected.military -= 5
                affected.population *= 0.98
                sounds.play('error')
                print(f"RIVOLTA: {affected.name} ha una rivolta popolare!")

    def check_win_conditions(self):
        """Verifica se il giocatore ha vinto o perso."""
        player = self.player_country
        if player.defeated:
            self.game_over = True
            self.winner = None
            return True
        # Vinci se controlli tutti i territori (o tutti i paesi sono sottomessi)
        all_defeated = all(c.defeated for c in self.countries.values() if c.name != player.name)
        if all_defeated:
            self.game_over = True
            self.winner = player.name
            return True
        return False

    def main_loop(self):
        """Ciclo principale del gioco."""
        while self.running and not self.game_over:
            self.turn += 1
            clear_screen()
            print_center(f"=== TURNO {self.turn} ===")
            # Evento casuale
            self.random_event()
            # Turno giocatore
            self.player_turn()
            if self.game_over or not self.running:
                break
            # Turno IA
            print("\n--- Turno degli altri paesi ---")
            self.ai_turn()
            # Controlla vittoria
            if self.check_win_conditions():
                break
            time.sleep(1)

        # Fine partita
        if self.game_over:
            clear_screen()
            if self.winner == self.player_country.name:
                print_center("🎉 HAI VINTO! Hai conquistato il mondo! 🎉")
                sounds.play('victory')
            else:
                print_center("💀 Sei stato sconfitto. GAME OVER 💀")
                sounds.play('defeat')
            print("\nGrazie per aver giocato a GEOPOLITICA!")
        else:
            print("Partita salvata. Arrivederci!")

# -------------------- MAIN --------------------
def main():
    try:
        game = Game()
        game.main_loop()
    except KeyboardInterrupt:
        print("\nGioco interrotto dall'utente.")
        sys.exit(0)

if __name__ == "__main__":
    main()