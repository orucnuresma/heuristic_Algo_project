import random

# ==========================================
# 1. INITIALIZATION (Başlangıç Popülasyonu)
# ==========================================
def initialize_chromosome(breakfast_ids, lunch_ids):
    """
    Kahvaltı ve öğle+akşam listelerini bağımsız olarak karıştırıp rastgele bir çözüm üretir.
    İki parça birbirinden bağımsız karıştırılır.
    """
    breakfast_part = random.sample(breakfast_ids, len(breakfast_ids))
    lunch_part = random.sample(lunch_ids, len(lunch_ids))
    
    return breakfast_part, lunch_part


# ==========================================
# 2. CROSSOVER (OX - Order Crossover)
# ==========================================
def _ox_crossover_single_part(p1, p2):
    """
    Tek bir parça için standart OX (Order Crossover) işlemi.
    Ebeveyn 1'den bir alt dizi alınır, kalanlar Ebeveyn 2'nin sırasına göre doldurulur.
    """
    size = len(p1)
    # İki rastgele kesim noktası belirle
    start, end = sorted(random.sample(range(size), 2))
    
    child = [None] * size
    
    # Adım 1: Ebeveyn 1'den seçilen aralığı direkt kopyala
    child[start:end+1] = p1[start:end+1]
    
    # Adım 2: Ebeveyn 2'deki elemanları, ikinci kesim noktasından başlayarak tara ve boşluklara yerleştir
    fill_idx = (end + 1) % size
    p2_idx = (end + 1) % size
    
    while None in child:
        if p2[p2_idx] not in child:
            child[fill_idx] = p2[p2_idx]
            fill_idx = (fill_idx + 1) % size
        p2_idx = (p2_idx + 1) % size
            
    return child

def apply_crossover(parent1_break, parent1_lunch, parent2_break, parent2_lunch, crossover_rate=0.9):
    """
    Kılavuza göre çaprazlama oranı (p_c) 0.9'dur.
    Kahvaltı ve öğle/akşam parçalarına ayrı ayrı uygulanır.
    """
    if random.random() > crossover_rate:
        # 0.1 ihtimalle çaprazlama olmazsa ebeveynler aynen kopyalanır
        return parent1_break[:], parent1_lunch[:]
    
    child_break = _ox_crossover_single_part(parent1_break, parent2_break)
    child_lunch = _ox_crossover_single_part(parent1_lunch, parent2_lunch)
    
    return child_break, child_lunch


# ==========================================
# 3. MUTATION (Swap Mutasyonu)
# ==========================================
def _swap_mutate_single_part(chromosome_part):
    """
    Tek bir parça üzerinde Swap (Yer değiştirme) mutasyonu.
    Kılavuz kuralı: Mutasyon oranı p_m = 1/n (n = parça uzunluğu).
    """
    size = len(chromosome_part)
    mutation_rate = 1.0 / size 
    
    mutated = chromosome_part[:]
    for i in range(size):
        if random.random() < mutation_rate:
            # Rastgele başka bir indeks seç ve yerlerini değiştir
            swap_idx = random.randint(0, size - 1)
            mutated[i], mutated[swap_idx] = mutated[swap_idx], mutated[i]
            
    return mutated

def apply_mutation(breakfast_part, lunch_part):
    """
    Kahvaltı ve öğle/akşam parçalarına ayrı ayrı bağımsız mutasyon uygular.
    """
    mutated_break = _swap_mutate_single_part(breakfast_part)
    mutated_lunch = _swap_mutate_single_part(lunch_part)
    
    return mutated_break, mutated_lunch