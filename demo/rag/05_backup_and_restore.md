# Zálohovanie a obnova — fiktívna služba Orion

SYNTETICKÉ DEMO: Žiadne údaje v tomto dokumente nepotvrdzujú stav reálneho servera.

Orion poskytuje interné finančné reporty. Plná databázová záloha sa spúšťa každý deň o 02:00 Europe/Bratislava. Inkrementálne zálohy sa vytvárajú každú hodinu. Denné zálohy sa uchovávajú 35 dní a mesačné 12 mesiacov. Zálohy sú šifrované a kľúče spravuje bezpečnostný tím oddelene od úložiska záloh.

Cieľ RPO je jedna hodina a cieľ RTO štyri hodiny. RPO znamená maximálnu cieľovú stratu dát v čase; RTO je cieľový čas obnovy služby. Obnovu povoľuje vlastník Finance Operations spolu s incident commanderom. Najprv sa obnovuje do izolovaného prostredia, potom sa overia počty záznamov a kontrolné súčty. Prepnutie produkcie vyžaduje samostatné schválenie.

Test obnovy sa robí prvý utorok každého mesiaca. Posledný fiktívny test z 6. októbra 2026 trval 2 hodiny 18 minút a bol úspešný. Tento historický výsledok nepotvrdzuje úspech ďalších záloh.
