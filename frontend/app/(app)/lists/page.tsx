"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Archive, Check, Pencil, Plus, Trash2 } from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { shoppingListsService } from "@/services/shoppingLists";
import type { ShoppingList } from "@/types/shoppingLists";
import PageHeader from "@/components/consumer/PageHeader";
import StatePanel from "@/components/consumer/StatePanel";
import { ListChecks } from "lucide-react";
import QuantityControl from "@/components/consumer/QuantityControl";

export default function ShoppingListsPage() {
  const router = useRouter();
  const [lists, setLists] = useState<readonly ShoppingList[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selected = useMemo(() => lists.find((list) => list.id === selectedId) ?? null, [lists, selectedId]);

  useEffect(() => {
    let mounted = true;
    void shoppingListsService.list().then((result) => {
      if (!mounted) return;
      setLists(result);
      setSelectedId(result.find((list) => !list.archived)?.id ?? result[0]?.id ?? null);
    }).catch((cause: unknown) => {
      if (mounted) setError(cause instanceof Error ? cause.message : "Shopping lists are unavailable.");
    }).finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, []);

  function acceptUpdatedList(updated: ShoppingList) {
    setLists((current) => current.map((list) => list.id === updated.id ? updated : list));
    setSelectedId(updated.id);
  }

  async function createList(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const name = String(new FormData(form).get("name") ?? "").trim();
    if (!name || saving) return;
    setSaving(true); setError(null);
    try {
      const created = await shoppingListsService.create(name);
      setLists((current) => [created, ...current]); setSelectedId(created.id); form.reset();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not create this list."); }
    finally { setSaving(false); }
  }

  async function addItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || selected.archived || saving) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const query = String(data.get("query") ?? "").trim();
    const quantity = Number(data.get("quantity") ?? 1);
    if (!query || !Number.isInteger(quantity) || quantity < 1 || quantity > 999) {
      setError("Enter an item and a quantity from 1 to 999."); return;
    }
    setSaving(true); setError(null);
    try {
      acceptUpdatedList(await shoppingListsService.addItem(selected.id, { query, quantity }));
      form.reset();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not save this item."); }
    finally { setSaving(false); }
  }

  async function changeQuantity(itemId: string, quantity: number) {
    if (!selected || selected.archived || saving) return;
    if (quantity < 1) { await removeItem(itemId); return; }
    setSaving(true); setError(null);
    try { acceptUpdatedList(await shoppingListsService.updateItem(selected.id, itemId, quantity)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not update quantity."); }
    finally { setSaving(false); }
  }

  async function removeItem(itemId: string) {
    if (!selected || selected.archived || saving) return;
    setSaving(true); setError(null);
    try {
      await shoppingListsService.removeItem(selected.id, itemId);
      setLists((current) => current.map((list) => list.id === selected.id
        ? { ...list, revision: list.revision + 1, items: list.items.filter((item) => item.id !== itemId) }
        : list));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not remove this item."); }
    finally { setSaving(false); }
  }

  async function renameList(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || saving) return;
    const form = event.currentTarget;
    const name = String(new FormData(form).get("name") ?? "").trim();
    if (!name) { setError("List name cannot be blank."); return; }
    setSaving(true); setError(null);
    try { acceptUpdatedList(await shoppingListsService.update(selected.id, { name })); setEditingName(false); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not rename this list."); }
    finally { setSaving(false); }
  }

  async function toggleArchive() {
    if (!selected || saving) return;
    setSaving(true); setError(null);
    try { acceptUpdatedList(await shoppingListsService.update(selected.id, { archived: !selected.archived })); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not update this list."); }
    finally { setSaving(false); }
  }

  return (
    <AppShell>
      <div className="space-y-8">
        <PageHeader eyebrow="Your shopping" title="Shopping lists" description="Keep requests and exact product selections in your Cartel account. Every revision stays tied to the evidence used for planning." />

        <form onSubmit={createList} className="flex max-w-xl gap-3">
          <input name="name" aria-label="New list name" placeholder="List name" maxLength={120} required className="h-10 min-w-0 flex-1 rounded-md border border-border bg-background px-3 text-sm" />
          <Button type="submit" disabled={saving}><Plus className="h-4 w-4" aria-hidden="true" />Create list</Button>
        </form>

        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        {loading ? <p role="status" className="text-sm text-muted-foreground">Loading your lists…</p> : lists.length === 0 ? (
          <StatePanel icon={ListChecks} title="Your first list is ready to create" description="Name a list above, then add an item to review or choose an exact verified product from Search." />
        ) : (
          <div className="grid gap-8 lg:grid-cols-[15rem_minmax(0,1fr)]">
            <nav aria-label="Shopping lists" className="space-y-1 border-b border-border pb-4 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-5">
              {lists.map((list) => <button key={list.id} type="button" onClick={() => { setSelectedId(list.id); setEditingName(false); }} aria-current={list.id === selectedId ? "page" : undefined} className={`flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-left text-sm ${list.id === selectedId ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:bg-muted/60"}`}>
                <span className="truncate">{list.name}</span><span className="text-xs tabular-nums">{list.items.length}</span>
              </button>)}
            </nav>

            {selected && <section aria-labelledby="selected-list-heading" className="min-w-0 space-y-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  {editingName ? <form onSubmit={renameList} className="flex gap-2"><input name="name" aria-label="List name" defaultValue={selected.name} maxLength={120} required className="h-9 min-w-0 rounded-md border border-border bg-background px-3 text-sm" /><Button type="submit" size="sm" disabled={saving}><Check className="h-4 w-4" aria-hidden="true" />Save</Button></form> : <div className="flex items-center gap-2"><h2 id="selected-list-heading" className="truncate text-xl font-semibold">{selected.name}</h2>{!selected.archived && <Button variant="ghost" size="icon-sm" aria-label="Rename list" onClick={() => setEditingName(true)}><Pencil className="h-4 w-4" aria-hidden="true" /></Button>}</div>}
                  <p className="mt-1 text-sm text-muted-foreground">Revision {selected.revision}{selected.archived ? " · Archived" : ""}</p>
                </div>
                <Button variant="outline" size="sm" onClick={() => void toggleArchive()} disabled={saving}>
                  <Archive className="h-4 w-4" aria-hidden="true" />{selected.archived ? "Restore list" : "Archive"}
                </Button>
                {!selected.archived && selected.items.length > 0 && <Button size="sm" onClick={() => router.push(`/optimize?list_id=${encodeURIComponent(selected.id)}&revision=${selected.revision}`)}>Optimize list</Button>}
              </div>

              {!selected.archived && <form onSubmit={addItem} className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_7rem_auto]">
                <input name="query" aria-label="Item to add" placeholder="Add an item you need" maxLength={300} required className="h-10 rounded-md border border-border bg-background px-3 text-sm" />
                <input name="quantity" aria-label="Quantity" type="number" min={1} max={999} defaultValue={1} required className="h-10 rounded-md border border-border bg-background px-3 text-sm" />
                <Button type="submit" disabled={saving}><Plus className="h-4 w-4" aria-hidden="true" />Add item</Button>
              </form>}

              {selected.items.length === 0 ? <div className="border-t border-border py-10"><h3 className="font-medium">This list is empty</h3><p className="mt-2 text-sm text-muted-foreground">Search verified products or add an item to review above.</p></div> :
                <div className="divide-y divide-border border-y border-border">
                  {selected.items.map((item) => <article key={item.id} className="flex flex-wrap items-center justify-between gap-4 py-4">
                    <div className="min-w-0 flex-1"><h3 className="font-medium">{item.display_name ?? item.query}</h3><p className="mt-1 text-xs text-muted-foreground">{item.resolution_status === "exact_confirmed" ? "Exact product saved" : "Request saved · product match still unresolved"}{item.unit ? ` · ${item.unit}` : ""}</p></div>
                    <div className="flex items-center gap-2"><QuantityControl label={item.display_name ?? item.query} value={item.quantity} disabled={saving || selected.archived} onChange={(quantity) => void changeQuantity(item.id, quantity)} /><Button variant="ghost" size="icon-sm" aria-label={`Remove ${item.query}`} disabled={saving || selected.archived} onClick={() => void removeItem(item.id)}><Trash2 className="h-4 w-4" aria-hidden="true" /></Button></div>
                  </article>)}
                </div>}
            </section>}
          </div>
        )}
      </div>
    </AppShell>
  );
}
