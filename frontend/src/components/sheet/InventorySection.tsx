import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Backpack,
  Check,
  Coins,
  Minus,
  Package,
  Plus,
  Search,
  Shield,
  ShieldCheck,
  Sparkles,
  Sword,
  Trash2,
  Wrench,
  X,
} from "lucide-react";
import { useCharacterStore } from "@/store/characterStore";
import { api, type EquipmentCatalogItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export interface InventoryCoins {
  cp: number;
  sp: number;
  ep: number;
  gp: number;
  pp: number;
}

export type ItemCategory =
  | "Weapon"
  | "Armor"
  | "Shield"
  | "Gear"
  | "Tool"
  | "Consumable"
  | "Treasure"
  | "Other";

export interface InventoryItem {
  id: string;
  name: string;
  quantity: number;
  category?: ItemCategory;
  source?: string;
  notes?: string;
  equipped?: boolean;
  base_item?: string;
  attack_bonus?: number;
  damage_bonus?: number;
  ac_bonus?: number;
  damage_dice?: string;
  damage_type?: string;
}

export interface CharacterInventory {
  coins: InventoryCoins;
  items: InventoryItem[];
}

interface Props {
  c: Record<string, unknown>;
}

function isShield(item: { name: string; category?: string; base_item?: string }): boolean {
  return (
    item.category === "Shield" ||
    item.name.toLowerCase() === "shield" ||
    item.name.toLowerCase().includes("shield") ||
    item.base_item?.toLowerCase() === "shield" ||
    item.base_item?.toLowerCase().includes("shield") === true
  );
}

function isBodyArmor(item: { name: string; category?: string; base_item?: string }): boolean {
  return item.category === "Armor" && !isShield(item);
}

function isEquippable(item: InventoryItem): boolean {
  return (
    item.category === "Weapon" ||
    item.category === "Armor" ||
    item.category === "Shield" ||
    isShield(item) ||
    Boolean(item.ac_bonus && item.ac_bonus > 0) ||
    Boolean(item.attack_bonus && item.attack_bonus > 0) ||
    Boolean(item.damage_bonus && item.damage_bonus > 0)
  );
}

function getInitialInventory(
  c: Record<string, unknown>,
  choicesMade: Record<string, unknown>,
): CharacterInventory {
  if (choicesMade.inventory && typeof choicesMade.inventory === "object") {
    const inv = choicesMade.inventory as CharacterInventory;
    const rawItems = Array.isArray(inv.items) ? inv.items : [];
    const items = rawItems.map((item) => {
      const equippable = isEquippable(item);
      const cat = isShield(item) ? "Shield" : item.category;
      return {
        ...item,
        category: cat,
        equipped: item.equipped !== undefined ? item.equipped : equippable,
      };
    });
    return {
      coins: {
        cp: Math.max(0, Number(inv.coins?.cp) || 0),
        sp: Math.max(0, Number(inv.coins?.sp) || 0),
        ep: Math.max(0, Number(inv.coins?.ep) || 0),
        gp: Math.max(0, Number(inv.coins?.gp) || 0),
        pp: Math.max(0, Number(inv.coins?.pp) || 0),
      },
      items,
    };
  }

  // Fallback: derive from calculated c.equipment
  const eq = (c.equipment && typeof c.equipment === "object"
    ? c.equipment
    : {}) as Record<string, unknown>;
  const startingGold = typeof eq.gold === "number" ? eq.gold : 0;
  const items: InventoryItem[] = [];

  const weapons = Array.isArray(eq.weapons) ? eq.weapons : [];
  weapons.forEach((w: any, idx: number) => {
    const name = w.display_name || w.name || "Weapon";
    const props = w.properties || {};
    const notesParts: string[] = [];
    if (props.damage && props.damage_type) {
      notesParts.push(`${props.damage} ${props.damage_type}`);
    }
    if (Array.isArray(props.properties) && props.properties.length > 0) {
      notesParts.push(props.properties.join(", "));
    }
    if (props.mastery) {
      notesParts.push(`Mastery: ${props.mastery}`);
    }

    items.push({
      id: `wep-${idx}-${name}`,
      name,
      base_item: w.name || name,
      quantity: typeof w.quantity === "number" ? w.quantity : 1,
      category: "Weapon",
      source: w.source || "Starting Gear",
      equipped: true,
      notes: notesParts.join(" · ") || undefined,
      attack_bonus: typeof w.attack_bonus === "number" ? w.attack_bonus : 0,
      damage_bonus: typeof w.damage_bonus === "number" ? w.damage_bonus : 0,
    });
  });

  const armor = Array.isArray(eq.armor) ? eq.armor : [];
  armor.forEach((a: any, idx: number) => {
    const name = a.display_name || a.name || "Armor";
    const shield = a.category === "Shield" || name.toLowerCase().includes("shield");
    items.push({
      id: `arm-${idx}-${name}`,
      name,
      base_item: a.name || name,
      quantity: 1,
      category: shield ? "Shield" : "Armor",
      source: a.source || "Starting Gear",
      equipped: true,
      ac_bonus: typeof a.ac_bonus === "number" ? a.ac_bonus : 0,
      notes: a.notes || undefined,
    });
  });

  const gear = Array.isArray(eq.items) ? eq.items : [];
  gear.forEach((it: any, idx: number) => {
    const name = typeof it === "string" ? it : it.name || "Gear";
    const source = typeof it === "object" ? it.source : undefined;
    items.push({
      id: `item-${idx}-${name}`,
      name,
      quantity:
        typeof it === "object" && typeof it.quantity === "number"
          ? it.quantity
          : 1,
      category: "Gear",
      source: source || "Starting Gear",
      equipped: false,
    });
  });

  return {
    coins: {
      cp: 0,
      sp: 0,
      ep: 0,
      gp: startingGold,
      pp: 0,
    },
    items,
  };
}

const CATEGORY_TABS: Array<{ label: string; value: string }> = [
  { label: "All", value: "all" },
  { label: "Equipped", value: "equipped" },
  { label: "Weapons", value: "weapons" },
  { label: "Armor & Shields", value: "armor" },
  { label: "Gear & Tools", value: "gear" },
  { label: "Consumables", value: "consumable" },
  { label: "Treasure", value: "treasure" },
];

export function InventorySection({ c }: Props) {
  const choicesMade = useCharacterStore((s) => s.choicesMade);
  const setChoice = useCharacterStore((s) => s.setChoice);

  const inventory: CharacterInventory = useMemo(() => {
    return getInitialInventory(c, choicesMade);
  }, [c, choicesMade]);

  const [activeTab, setActiveTab] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [dialogTab, setDialogTab] = useState<"catalog" | "custom">("catalog");

  // Catalog tab filter state inside modal
  const [catalogSearch, setCatalogSearch] = useState("");
  const [catalogCategory, setCatalogCategory] = useState<string>("all");
  const [catalogItemQty, setCatalogItemQty] = useState<Record<string, number>>({});
  const [recentlyAddedId, setRecentlyAddedId] = useState<string | null>(null);

  // Custom item tab form state inside modal
  const [customName, setCustomName] = useState("");
  const [customBaseItem, setCustomBaseItem] = useState("");
  const [customQty, setCustomQty] = useState(1);
  const [customCategory, setCustomCategory] = useState<ItemCategory>("Weapon");
  const [customAtkBonus, setCustomAtkBonus] = useState<number>(0);
  const [customDmgBonus, setCustomDmgBonus] = useState<number>(0);
  const [customAcBonus, setCustomAcBonus] = useState<number>(0);
  const [customDmgDice, setCustomDmgDice] = useState<string>("");
  const [customDmgType, setCustomDmgType] = useState<string>("Slashing");
  const [customEquipped, setCustomEquipped] = useState<boolean>(true);
  const [customNotes, setCustomNotes] = useState<string>("");

  // Query equipment catalog from API
  const { data: catalogItems = [], isLoading: isLoadingCatalog } = useQuery({
    queryKey: ["equipmentCatalog"],
    queryFn: () => api.catalog.getEquipment(),
    staleTime: 1000 * 60 * 30, // 30 minutes
  });

  function updateInventory(next: CharacterInventory) {
    setChoice("inventory", next);
  }

  function handleCoinChange(denom: keyof InventoryCoins, delta: number) {
    const current = inventory.coins[denom];
    const nextVal = Math.max(0, current + delta);
    updateInventory({
      ...inventory,
      coins: {
        ...inventory.coins,
        [denom]: nextVal,
      },
    });
  }

  function handleCoinSet(denom: keyof InventoryCoins, val: number) {
    updateInventory({
      ...inventory,
      coins: {
        ...inventory.coins,
        [denom]: Math.max(0, Math.floor(val)),
      },
    });
  }

  function handleItemQtyChange(itemId: string, delta: number) {
    const updated = inventory.items
      .map((it) => {
        if (it.id !== itemId) return it;
        const nextQty = it.quantity + delta;
        return nextQty > 0 ? { ...it, quantity: nextQty } : null;
      })
      .filter((it): it is InventoryItem => it !== null);

    updateInventory({
      ...inventory,
      items: updated,
    });
  }

  function handleDeleteItem(itemId: string) {
    updateInventory({
      ...inventory,
      items: inventory.items.filter((it) => it.id !== itemId),
    });
  }

  function handleToggleEquip(itemId: string) {
    const target = inventory.items.find((it) => it.id === itemId);
    if (!target) return;
    const nextEquipped = !target.equipped;

    const updated = inventory.items.map((it) => {
      if (it.id === itemId) {
        return { ...it, equipped: nextEquipped };
      }
      // If equipping a body armor, unequip other body armor
      if (nextEquipped && isBodyArmor(target)) {
        if (isBodyArmor(it)) {
          return { ...it, equipped: false };
        }
      }
      // If equipping a shield, unequip other shields
      if (nextEquipped && isShield(target)) {
        if (isShield(it)) {
          return { ...it, equipped: false };
        }
      }
      return it;
    });

    updateInventory({
      ...inventory,
      items: updated,
    });
  }

  // Add item from catalog
  function handleAddCatalogItem(item: EquipmentCatalogItem) {
    const qty = Math.max(1, catalogItemQty[item.id] || 1);
    const equippable = item.category === "Weapon" || item.category === "Armor" || item.category === "Shield";
    const nextEquipped = equippable;

    let notes = "";
    if (item.damage) {
      notes += `${item.damage} ${item.damage_type || ""}`.trim();
    }
    if (item.properties && item.properties.length > 0) {
      notes += (notes ? " · " : "") + item.properties.join(", ");
    }
    if (item.mastery) {
      notes += (notes ? " · " : "") + `Mastery: ${item.mastery}`;
    }
    if (item.ac_formula) {
      notes += (notes ? " · " : "") + `AC: ${item.ac_formula}`;
    }

    const newItem: InventoryItem = {
      id: `cat-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      name: item.name,
      base_item: item.name,
      category: item.category as ItemCategory,
      quantity: qty,
      source: "Catalog",
      equipped: nextEquipped,
      notes: notes || undefined,
      attack_bonus: 0,
      damage_bonus: 0,
      ac_bonus: 0,
      damage_dice: item.damage,
      damage_type: item.damage_type,
    };

    // Apply exclusivity if equipped
    const updated = inventory.items.map((it) => {
      if (nextEquipped && isBodyArmor(newItem) && isBodyArmor(it)) {
        return { ...it, equipped: false };
      }
      if (nextEquipped && isShield(newItem) && isShield(it)) {
        return { ...it, equipped: false };
      }
      return it;
    });

    updateInventory({
      ...inventory,
      items: [newItem, ...updated],
    });

    // Provide visual feedback
    setRecentlyAddedId(item.id);
    setTimeout(() => {
      setRecentlyAddedId((curr) => (curr === item.id ? null : curr));
    }, 1500);
  }

  // When picking a base item template in the custom item tab
  function handleSelectBaseItem(baseName: string) {
    setCustomBaseItem(baseName);
    const found = catalogItems.find((i) => i.name === baseName);
    if (!found) return;

    if (!customName || customName === customBaseItem) {
      setCustomName(found.name);
    }
    setCustomCategory(found.category as ItemCategory);
    if (found.damage) {
      setCustomDmgDice(found.damage);
    }
    if (found.damage_type) {
      setCustomDmgType(found.damage_type);
    }
    setCustomEquipped(found.category === "Weapon" || found.category === "Armor" || found.category === "Shield");
  }

  // Submit custom item form
  function handleAddCustomItem(e: React.FormEvent) {
    e.preventDefault();
    const name = customName.trim();
    if (!name) return;

    const newItem: InventoryItem = {
      id: `custom-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      name,
      base_item: customBaseItem.trim() || undefined,
      quantity: Math.max(1, customQty),
      category: customCategory,
      equipped: customEquipped,
      notes: customNotes.trim() || undefined,
      attack_bonus: customAtkBonus !== 0 ? customAtkBonus : undefined,
      damage_bonus: customDmgBonus !== 0 ? customDmgBonus : undefined,
      ac_bonus: customAcBonus !== 0 ? customAcBonus : undefined,
      damage_dice: customDmgDice.trim() || undefined,
      damage_type: customDmgType.trim() || undefined,
      source: "Custom",
    };

    const updated = inventory.items.map((it) => {
      if (customEquipped && isBodyArmor(newItem) && isBodyArmor(it)) {
        return { ...it, equipped: false };
      }
      if (customEquipped && isShield(newItem) && isShield(it)) {
        return { ...it, equipped: false };
      }
      return it;
    });

    updateInventory({
      ...inventory,
      items: [newItem, ...updated],
    });

    // Reset form
    setCustomName("");
    setCustomBaseItem("");
    setCustomQty(1);
    setCustomAtkBonus(0);
    setCustomDmgBonus(0);
    setCustomAcBonus(0);
    setCustomDmgDice("");
    setCustomNotes("");
    setIsAddDialogOpen(false);
  }

  // Filtered catalog items for the modal
  const filteredCatalogItems = useMemo(() => {
    return catalogItems.filter((item) => {
      if (catalogCategory !== "all") {
        if (catalogCategory === "Weapon" && item.category !== "Weapon") return false;
        if (catalogCategory === "Armor" && item.category !== "Armor") return false;
        if (catalogCategory === "Shield" && item.category !== "Shield") return false;
        if (catalogCategory === "Gear" && item.category !== "Gear") return false;
        if (catalogCategory === "Tool" && item.category !== "Tool") return false;
        if (catalogCategory === "Consumable" && item.category !== "Consumable") return false;
      }
      if (catalogSearch.trim()) {
        const q = catalogSearch.toLowerCase();
        const matchesName = item.name.toLowerCase().includes(q);
        const matchesSub = item.subcategory?.toLowerCase().includes(q) ?? false;
        const matchesProps = item.properties?.some((p) => p.toLowerCase().includes(q)) ?? false;
        return matchesName || matchesSub || matchesProps;
      }
      return true;
    });
  }, [catalogItems, catalogCategory, catalogSearch]);

  // Total gold equivalent
  const totalGoldValue = useMemo(() => {
    const { cp, sp, ep, gp, pp } = inventory.coins;
    return cp / 100 + sp / 10 + ep / 2 + gp + pp * 10;
  }, [inventory.coins]);

  // Main sheet inventory items filtering
  const filteredItems = useMemo(() => {
    return inventory.items.filter((item) => {
      // Category tabs
      if (activeTab === "equipped") {
        if (!item.equipped) return false;
      } else if (activeTab === "weapons") {
        if (item.category !== "Weapon") return false;
      } else if (activeTab === "armor") {
        if (item.category !== "Armor" && item.category !== "Shield" && !isShield(item)) return false;
      } else if (activeTab === "gear") {
        if (item.category !== "Gear" && item.category !== "Tool") return false;
      } else if (activeTab === "consumable") {
        if (item.category !== "Consumable") return false;
      } else if (activeTab === "treasure") {
        if (item.category !== "Treasure") return false;
      }

      // Search filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesName = item.name.toLowerCase().includes(query);
        const matchesNotes = item.notes?.toLowerCase().includes(query) ?? false;
        const matchesBase = item.base_item?.toLowerCase().includes(query) ?? false;
        return matchesName || matchesNotes || matchesBase;
      }

      return true;
    });
  }, [inventory.items, activeTab, searchQuery]);

  return (
    <section className="mt-6 rounded-xl border border-border bg-card p-5 sm:p-6 shadow-sm">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border/70 pb-4">
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-primary/10 p-2 text-primary">
            <Backpack className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-display text-xl font-bold text-foreground">
              Inventory &amp; Currency
            </h2>
            <p className="text-xs text-muted-foreground">
              Equip weapons, armors, shields, and magic items to automatically update your combat stats.
            </p>
          </div>
        </div>

        <Button
          size="sm"
          onClick={() => setIsAddDialogOpen(true)}
          className="gap-1.5"
        >
          <Plus className="h-4 w-4" /> Add Item
        </Button>
      </div>

      {/* ── Currency Pouches ────────────────────────────────────── */}
      <div className="mt-5 rounded-xl border border-border/80 bg-secondary/30 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground font-semibold">
            <Coins className="h-4 w-4 text-amber-500" />
            <span>Coin Pouches</span>
          </div>
          <div className="text-xs font-medium text-muted-foreground">
            Total Wealth:{" "}
            <span className="font-bold text-foreground">
              {totalGoldValue.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}{" "}
              GP
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {/* Copper */}
          <CoinPouch
            label="Copper (CP)"
            short="CP"
            badgeColor="bg-amber-900/15 text-amber-800 dark:text-amber-400 border-amber-800/30"
            amount={inventory.coins.cp}
            onDelta={(d) => handleCoinChange("cp", d)}
            onSet={(v) => handleCoinSet("cp", v)}
          />

          {/* Silver */}
          <CoinPouch
            label="Silver (SP)"
            short="SP"
            badgeColor="bg-slate-500/15 text-slate-700 dark:text-slate-300 border-slate-400/30"
            amount={inventory.coins.sp}
            onDelta={(d) => handleCoinChange("sp", d)}
            onSet={(v) => handleCoinSet("sp", v)}
          />

          {/* Electrum */}
          <CoinPouch
            label="Electrum (EP)"
            short="EP"
            badgeColor="bg-cyan-500/15 text-cyan-800 dark:text-cyan-300 border-cyan-400/30"
            amount={inventory.coins.ep}
            onDelta={(d) => handleCoinChange("ep", d)}
            onSet={(v) => handleCoinSet("ep", v)}
          />

          {/* Gold */}
          <CoinPouch
            label="Gold (GP)"
            short="GP"
            badgeColor="bg-yellow-500/20 text-yellow-800 dark:text-yellow-400 border-yellow-500/40"
            amount={inventory.coins.gp}
            onDelta={(d) => handleCoinChange("gp", d)}
            onSet={(v) => handleCoinSet("gp", v)}
          />

          {/* Platinum */}
          <CoinPouch
            label="Platinum (PP)"
            short="PP"
            badgeColor="bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 border-indigo-400/30"
            amount={inventory.coins.pp}
            onDelta={(d) => handleCoinChange("pp", d)}
            onSet={(v) => handleCoinSet("pp", v)}
          />
        </div>
      </div>

      {/* ── Toolbar: Category filter + Search ───────────────────── */}
      <div className="mt-6 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Category tabs */}
        <div className="flex flex-wrap gap-1">
          {CATEGORY_TABS.map((tab) => {
            const isSelected = activeTab === tab.value;
            return (
              <button
                key={tab.value}
                type="button"
                onClick={() => setActiveTab(tab.value)}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                  isSelected
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground",
                )}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Search bar */}
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search items..."
            className="w-full rounded-lg border border-border bg-background/80 pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="absolute right-2.5 top-2.5 text-muted-foreground hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* ── Items List ─────────────────────────────────────────── */}
      <div className="mt-4">
        {filteredItems.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border/80 bg-background/40 py-10 text-center">
            <Package className="mx-auto h-8 w-8 text-muted-foreground/50 mb-2" />
            <p className="text-sm text-muted-foreground">
              {inventory.items.length === 0
                ? "No equipment in inventory yet."
                : "No items match your filter."}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsAddDialogOpen(true)}
              className="mt-3 gap-1.5"
            >
              <Plus className="h-3.5 w-3.5" /> Add an item
            </Button>
          </div>
        ) : (
          <ul className="divide-y divide-border/60 rounded-xl border border-border/80 bg-background/40 overflow-hidden">
            {filteredItems.map((item) => {
              const equippable = isEquippable(item);
              return (
                <li
                  key={item.id}
                  className={cn(
                    "flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 transition-colors",
                    item.equipped ? "bg-primary/[0.03] hover:bg-primary/[0.06]" : "hover:bg-secondary/20",
                  )}
                >
                  {/* Item Info */}
                  <div className="flex items-start gap-3 min-w-0 flex-1">
                    <div className="mt-0.5 rounded-lg border border-border/80 bg-card p-1.5 text-muted-foreground shrink-0">
                      <ItemCategoryIcon category={item.category} isEquipped={item.equipped} />
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className={cn("text-sm font-semibold truncate", item.equipped ? "text-foreground font-bold" : "text-foreground/90")}>
                          {item.name}
                        </p>

                        {/* Equipped badge */}
                        {item.equipped && (
                          <span className="inline-flex items-center gap-1 rounded border border-emerald-500/30 bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-400">
                            <ShieldCheck className="h-3 w-3" /> Equipped
                          </span>
                        )}

                        {/* Category badge */}
                        {item.category && (
                          <span className="rounded border border-border bg-secondary/60 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                            {item.category}
                          </span>
                        )}

                        {/* Magic attack / damage badge */}
                        {(Boolean(item.attack_bonus) || Boolean(item.damage_bonus)) && (
                          <span className="rounded border border-amber-500/30 bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-mono font-bold text-amber-700 dark:text-amber-400">
                            +{item.attack_bonus || 0} ATK / +{item.damage_bonus || 0} DMG
                          </span>
                        )}

                        {/* Magic AC bonus badge */}
                        {Boolean(item.ac_bonus && item.ac_bonus > 0) && (
                          <span className="rounded border border-blue-500/30 bg-blue-500/15 px-1.5 py-0.5 text-[10px] font-mono font-bold text-blue-700 dark:text-blue-400">
                            +{item.ac_bonus} AC
                          </span>
                        )}

                        {/* Base item badge if custom name differs */}
                        {item.base_item && item.base_item !== item.name && (
                          <span className="rounded bg-secondary/70 px-1.5 py-0.5 text-[10px] text-muted-foreground">
                            Base: {item.base_item}
                          </span>
                        )}

                        {/* Source badge */}
                        {item.source && (
                          <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] text-primary font-medium">
                            {item.source}
                          </span>
                        )}
                      </div>

                      {item.notes && (
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {item.notes}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Controls: Equip toggle + Quantity + Delete */}
                  <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                    {/* Equip / Unequip Toggle */}
                    {equippable && (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => handleToggleEquip(item.id)}
                        className={cn(
                          "h-7 px-2.5 text-xs font-semibold gap-1",
                          item.equipped
                            ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 hover:bg-destructive/10 hover:text-destructive border border-emerald-500/30"
                            : "hover:bg-primary/10 hover:text-primary",
                        )}
                        title={item.equipped ? "Unequip item" : "Equip item"}
                      >
                        {item.equipped ? (
                          <>
                            <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" /> Unequip
                          </>
                        ) : (
                          "Equip"
                        )}
                      </Button>
                    )}

                    {/* Quantity Stepper */}
                    <div className="flex items-center rounded-lg border border-border bg-background p-0.5 shadow-xs">
                      <button
                        type="button"
                        onClick={() => handleItemQtyChange(item.id, -1)}
                        className="rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                        title="Decrease quantity"
                        aria-label="Decrease quantity"
                      >
                        <Minus className="h-3 w-3" />
                      </button>
                      <span className="min-w-[2rem] text-center font-mono text-xs font-semibold text-foreground">
                        ×{item.quantity}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleItemQtyChange(item.id, 1)}
                        className="rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                        title="Increase quantity"
                        aria-label="Increase quantity"
                      >
                        <Plus className="h-3 w-3" />
                      </button>
                    </div>

                    {/* Delete button */}
                    <button
                      type="button"
                      onClick={() => handleDeleteItem(item.id)}
                      className="rounded-lg border border-transparent p-1.5 text-muted-foreground hover:border-destructive/30 hover:bg-destructive/10 hover:text-destructive transition-colors"
                      title={`Remove ${item.name}`}
                      aria-label={`Remove ${item.name}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* ── Add Equipment Dialog ───────────────────────────────── */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col p-0 overflow-hidden">
          <DialogHeader className="px-6 pt-5 pb-3 border-b border-border">
            <DialogTitle className="text-lg font-bold">Add Equipment &amp; Items</DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Browse standard game items or craft custom gear with attack, damage, and AC modifiers.
            </DialogDescription>

            {/* Modal Tabs */}
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setDialogTab("catalog")}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors",
                  dialogTab === "catalog"
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "bg-secondary text-muted-foreground hover:text-foreground",
                )}
              >
                Game Catalog
              </button>
              <button
                type="button"
                onClick={() => setDialogTab("custom")}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors",
                  dialogTab === "custom"
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "bg-secondary text-muted-foreground hover:text-foreground",
                )}
              >
                Custom &amp; Magic Items
              </button>
            </div>
          </DialogHeader>

          {/* Dialog Body */}
          <div className="flex-1 overflow-y-auto p-6">
            {dialogTab === "catalog" ? (
              <div>
                {/* Search & Category Filter */}
                <div className="flex flex-col sm:flex-row gap-2 mb-4">
                  <div className="relative flex-1">
                    <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                    <input
                      type="text"
                      value={catalogSearch}
                      onChange={(e) => setCatalogSearch(e.target.value)}
                      placeholder="Search weapons, armors, shields, gear..."
                      className="w-full rounded-lg border border-border bg-background pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {["all", "Weapon", "Armor", "Shield", "Gear", "Tool", "Consumable"].map((cat) => (
                      <button
                        key={cat}
                        type="button"
                        onClick={() => setCatalogCategory(cat)}
                        className={cn(
                          "px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors",
                          catalogCategory === cat
                            ? "bg-primary text-primary-foreground font-semibold"
                            : "bg-secondary/60 text-muted-foreground hover:bg-secondary hover:text-foreground",
                        )}
                      >
                        {cat === "all" ? "All" : cat}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Catalog items list */}
                {isLoadingCatalog ? (
                  <div className="py-12 text-center text-sm text-muted-foreground">
                    Loading catalog items...
                  </div>
                ) : filteredCatalogItems.length === 0 ? (
                  <div className="py-12 text-center text-sm text-muted-foreground">
                    No items found matching your filter.
                  </div>
                ) : (
                  <div className="divide-y divide-border/60 rounded-xl border border-border/80 bg-background/50 max-h-[48vh] overflow-y-auto">
                    {filteredCatalogItems.map((item) => {
                      const qty = catalogItemQty[item.id] || 1;
                      const isAdded = recentlyAddedId === item.id;
                      return (
                        <div
                          key={item.id}
                          className="flex items-center justify-between gap-3 p-3 hover:bg-secondary/20 transition-colors"
                        >
                          <div className="flex items-start gap-2.5 min-w-0 flex-1">
                            <div className="mt-0.5 rounded-md border border-border/60 bg-card p-1 text-muted-foreground shrink-0">
                              <ItemCategoryIcon category={item.category} />
                            </div>
                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span className="text-xs font-bold text-foreground">
                                  {item.name}
                                </span>
                                <span className="rounded border border-border bg-secondary/70 px-1 py-0.2 text-[9px] uppercase tracking-wider text-muted-foreground">
                                  {item.subcategory || item.category}
                                </span>
                                {item.cost && item.cost !== "—" && (
                                  <span className="text-[10px] text-muted-foreground">
                                    {item.cost}
                                  </span>
                                )}
                              </div>

                              {/* Key stats */}
                              <div className="mt-0.5 flex flex-wrap gap-x-2 text-[11px] text-muted-foreground">
                                {item.damage && (
                                  <span className="text-foreground/90 font-medium">
                                    {item.damage} {item.damage_type}
                                  </span>
                                )}
                                {item.mastery && (
                                  <span className="text-primary font-medium">
                                    Mastery: {item.mastery}
                                  </span>
                                )}
                                {item.ac_formula && (
                                  <span className="text-foreground/90 font-medium">
                                    AC {item.ac_formula}
                                  </span>
                                )}
                                {item.category === "Shield" && (
                                  <span className="text-foreground/90 font-medium">
                                    +2 AC
                                  </span>
                                )}
                                {item.properties && item.properties.length > 0 && (
                                  <span className="text-muted-foreground/80">
                                    ({item.properties.join(", ")})
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Add controls */}
                          <div className="flex items-center gap-2 shrink-0">
                            <div className="flex items-center rounded border border-border bg-background p-0.5">
                              <button
                                type="button"
                                onClick={() =>
                                  setCatalogItemQty((prev) => ({
                                    ...prev,
                                    [item.id]: Math.max(1, (prev[item.id] || 1) - 1),
                                  }))
                                }
                                className="p-0.5 text-muted-foreground hover:text-foreground"
                              >
                                <Minus className="h-3 w-3" />
                              </button>
                              <span className="w-6 text-center font-mono text-xs font-semibold">
                                {qty}
                              </span>
                              <button
                                type="button"
                                onClick={() =>
                                  setCatalogItemQty((prev) => ({
                                    ...prev,
                                    [item.id]: (prev[item.id] || 1) + 1,
                                  }))
                                }
                                className="p-0.5 text-muted-foreground hover:text-foreground"
                              >
                                <Plus className="h-3 w-3" />
                              </button>
                            </div>

                            <Button
                              size="sm"
                              variant={isAdded ? "outline" : "default"}
                              onClick={() => handleAddCatalogItem(item)}
                              className={cn(
                                "h-7 text-xs px-2.5 gap-1",
                                isAdded && "bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border border-emerald-500/40",
                              )}
                            >
                              {isAdded ? (
                                <>
                                  <Check className="h-3.5 w-3.5 text-emerald-600" /> Added
                                </>
                              ) : (
                                <>
                                  <Plus className="h-3.5 w-3.5" /> Add
                                </>
                              )}
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ) : (
              /* Custom Item Form */
              <form onSubmit={handleAddCustomItem} className="space-y-4">
                {/* Base Template Picker */}
                <div>
                  <label className="block text-xs uppercase tracking-wide text-muted-foreground mb-1">
                    Base Item Template (Optional)
                  </label>
                  <select
                    value={customBaseItem}
                    onChange={(e) => handleSelectBaseItem(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  >
                    <option value="">-- Start from scratch or pick a template --</option>
                    {catalogItems.map((item) => (
                      <option key={item.id} value={item.name}>
                        {item.name} ({item.category})
                      </option>
                    ))}
                  </select>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    Selecting a template pre-fills standard stats (e.g. Longsword 1d8 Slashing, Shield +2 AC).
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
                  <div className="sm:col-span-6">
                    <label className="block text-xs uppercase tracking-wide text-muted-foreground mb-1">
                      Item Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={customName}
                      onChange={(e) => setCustomName(e.target.value)}
                      placeholder="e.g. +1 Longsword, Shield of Faith, Ring of Protection"
                      className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>

                  <div className="sm:col-span-3">
                    <label className="block text-xs uppercase tracking-wide text-muted-foreground mb-1">
                      Category
                    </label>
                    <select
                      value={customCategory}
                      onChange={(e) => setCustomCategory(e.target.value as ItemCategory)}
                      className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                    >
                      <option value="Weapon">Weapon</option>
                      <option value="Armor">Armor</option>
                      <option value="Shield">Shield</option>
                      <option value="Gear">Gear / Wondrous Item</option>
                      <option value="Consumable">Consumable / Potion</option>
                      <option value="Tool">Tool</option>
                      <option value="Treasure">Treasure</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>

                  <div className="sm:col-span-3">
                    <label className="block text-xs uppercase tracking-wide text-muted-foreground mb-1">
                      Quantity
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={customQty}
                      onChange={(e) => setCustomQty(Math.max(1, parseInt(e.target.value) || 1))}
                      className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                </div>

                {/* Modifiers & Weapon Stats */}
                <div className="rounded-lg border border-border/80 bg-secondary/20 p-3 space-y-3">
                  <div className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-amber-500" /> Magic &amp; Combat Stat Modifiers
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-[11px] text-muted-foreground mb-1">
                        Attack Bonus (+X)
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="10"
                        value={customAtkBonus}
                        onChange={(e) => setCustomAtkBonus(parseInt(e.target.value) || 0)}
                        placeholder="0"
                        className="w-full rounded-md border border-input bg-background px-3 py-1 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] text-muted-foreground mb-1">
                        Damage Bonus (+X)
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="10"
                        value={customDmgBonus}
                        onChange={(e) => setCustomDmgBonus(parseInt(e.target.value) || 0)}
                        placeholder="0"
                        className="w-full rounded-md border border-input bg-background px-3 py-1 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] text-muted-foreground mb-1">
                        AC Bonus (+X)
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="10"
                        value={customAcBonus}
                        onChange={(e) => setCustomAcBonus(parseInt(e.target.value) || 0)}
                        placeholder="0"
                        className="w-full rounded-md border border-input bg-background px-3 py-1 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                      />
                      <span className="text-[10px] text-muted-foreground">
                        For +1 Armor, +1 Shield, or Ring of Protection.
                      </span>
                    </div>
                  </div>

                  {customCategory === "Weapon" && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-border/50">
                      <div>
                        <label className="block text-[11px] text-muted-foreground mb-1">
                          Damage Dice (e.g. 1d8, 2d6)
                        </label>
                        <input
                          type="text"
                          value={customDmgDice}
                          onChange={(e) => setCustomDmgDice(e.target.value)}
                          placeholder="e.g. 1d8"
                          className="w-full rounded-md border border-input bg-background px-3 py-1 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] text-muted-foreground mb-1">
                          Damage Type
                        </label>
                        <select
                          value={customDmgType}
                          onChange={(e) => setCustomDmgType(e.target.value)}
                          className="w-full rounded-md border border-input bg-background px-3 py-1 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                        >
                          <option value="Slashing">Slashing</option>
                          <option value="Piercing">Piercing</option>
                          <option value="Bludgeoning">Bludgeoning</option>
                          <option value="Fire">Fire</option>
                          <option value="Radiant">Radiant</option>
                          <option value="Cold">Cold</option>
                          <option value="Lightning">Lightning</option>
                          <option value="Force">Force</option>
                          <option value="Necrotic">Necrotic</option>
                          <option value="Psychic">Psychic</option>
                          <option value="Poison">Poison</option>
                          <option value="Acid">Acid</option>
                          <option value="Thunder">Thunder</option>
                        </select>
                      </div>
                    </div>
                  )}
                </div>

                {/* Equipped Checkbox */}
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="custom-equipped-check"
                    checked={customEquipped}
                    onChange={(e) => setCustomEquipped(e.target.checked)}
                    className="h-4 w-4 rounded border-input text-primary focus:ring-primary"
                  />
                  <label htmlFor="custom-equipped-check" className="text-xs font-medium text-foreground cursor-pointer">
                    Equipped immediately upon adding
                  </label>
                </div>

                {/* Notes */}
                <div>
                  <label className="block text-xs uppercase tracking-wide text-muted-foreground mb-1">
                    Notes / Description
                  </label>
                  <input
                    type="text"
                    value={customNotes}
                    onChange={(e) => setCustomNotes(e.target.value)}
                    placeholder="e.g. Deals 1d6 extra radiant damage, requires attunement, etc."
                    className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-border/70">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsAddDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" size="sm">
                    Add to Inventory
                  </Button>
                </div>
              </form>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </section>
  );
}

function CoinPouch({
  label,
  short,
  badgeColor,
  amount,
  onDelta,
  onSet,
}: {
  label: string;
  short: string;
  badgeColor: string;
  amount: number;
  onDelta: (d: number) => void;
  onSet: (v: number) => void;
}) {
  return (
    <div className="rounded-xl border border-border/80 bg-card/80 p-2.5 flex flex-col justify-between shadow-xs">
      <div className="flex items-center justify-between gap-1 mb-1.5">
        <span
          className={cn(
            "rounded-md border px-1.5 py-0.5 text-[10px] font-bold tracking-wider",
            badgeColor,
          )}
        >
          {short}
        </span>
        <span className="text-[10px] uppercase text-muted-foreground truncate" title={label}>
          {label.split(" ")[0]}
        </span>
      </div>

      <div className="flex items-center gap-1 mt-1">
        <button
          type="button"
          onClick={() => onDelta(-1)}
          className="rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          title={`Minus 1 ${short}`}
        >
          <Minus className="h-3 w-3" />
        </button>

        <input
          type="number"
          min="0"
          value={amount}
          onChange={(e) => onSet(parseInt(e.target.value) || 0)}
          className="w-full text-center font-mono text-sm font-bold bg-transparent border-0 focus:outline-none focus:ring-1 focus:ring-primary/40 rounded px-1"
        />

        <button
          type="button"
          onClick={() => onDelta(1)}
          className="rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          title={`Plus 1 ${short}`}
        >
          <Plus className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}

function ItemCategoryIcon({ category, isEquipped }: { category?: ItemCategory; isEquipped?: boolean }) {
  switch (category) {
    case "Weapon":
      return <Sword className={cn("h-4 w-4", isEquipped ? "text-amber-500" : "text-muted-foreground")} />;
    case "Armor":
      return <Shield className={cn("h-4 w-4", isEquipped ? "text-blue-500" : "text-muted-foreground")} />;
    case "Shield":
      return <ShieldCheck className={cn("h-4 w-4", isEquipped ? "text-emerald-500" : "text-muted-foreground")} />;
    case "Consumable":
      return <Sparkles className="h-4 w-4 text-purple-500" />;
    case "Tool":
      return <Wrench className="h-4 w-4 text-cyan-500" />;
    case "Treasure":
      return <Coins className="h-4 w-4 text-yellow-500" />;
    default:
      return <Package className="h-4 w-4 text-muted-foreground" />;
  }
}
