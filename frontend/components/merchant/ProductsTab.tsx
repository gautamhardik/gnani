"use client";

import React, { useState } from "react";
import {
  Search,
  Plus,
  Edit2,
  CheckCircle,
  XCircle,
  Loader2,
  RefreshCw,
  AlertCircle,
  Tag,
} from "lucide-react";
import { Product, ProductCreateRequest, ProductUpdateRequest } from "@/types/merchant";
import { createProduct, updateProduct } from "@/lib/merchantApi";

interface ProductsTabProps {
  products: Product[];
  isLoading: boolean;
  onRefresh: () => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}

export function ProductsTab({
  products,
  isLoading,
  onRefresh,
  searchQuery,
  onSearchChange,
}: ProductsTabProps) {
  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Add Form state
  const [addName, setAddName] = useState("");
  const [addCategory, setAddCategory] = useState("Dairy");
  const [addPrice, setAddPrice] = useState("");
  const [addBaseUnit, setAddBaseUnit] = useState("piece");
  const [addPackageType, setAddPackageType] = useState("packet");
  const [addInitialStock, setAddInitialStock] = useState("20");
  const [addLowStock, setAddLowStock] = useState("5");
  const [addAliases, setAddAliases] = useState("");

  // Edit Form state
  const [editName, setEditName] = useState("");
  const [editPrice, setEditPrice] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editIsActive, setEditIsActive] = useState(true);

  const handleOpenEdit = (p: Product) => {
    setEditingProduct(p);
    setEditName(p.name);
    setEditPrice(p.price.toString());
    setEditCategory(p.category);
    setEditIsActive(p.is_active);
    setFormError(null);
  };

  const handleSaveAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addName.trim() || !addPrice) {
      setFormError("Kripya product ka naam aur kimat daalein.");
      return;
    }

    const priceNum = parseFloat(addPrice);
    if (isNaN(priceNum) || priceNum <= 0) {
      setFormError("Kripya sahi kimat daalein (> 0).");
      return;
    }

    setIsSubmitting(true);
    setFormError(null);

    try {
      const aliasList = addAliases
        .split(",")
        .map((a) => a.trim())
        .filter((a) => a.length > 0);

      const payload: ProductCreateRequest = {
        name: addName.trim(),
        category: addCategory,
        price: priceNum,
        base_unit: addBaseUnit,
        package_type: addPackageType,
        initial_stock: parseFloat(addInitialStock) || 0,
        low_stock_threshold: parseFloat(addLowStock) || 5,
        aliases: aliasList,
      };

      await createProduct(payload);
      setShowAddModal(false);
      // Reset
      setAddName("");
      setAddPrice("");
      setAddAliases("");
      onRefresh();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Product creation failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProduct) return;

    const priceNum = parseFloat(editPrice);
    if (isNaN(priceNum) || priceNum <= 0) {
      setFormError("Kripya sahi kimat daalein (> 0).");
      return;
    }

    setIsSubmitting(true);
    setFormError(null);

    try {
      const payload: ProductUpdateRequest = {
        name: editName.trim(),
        price: priceNum,
        category: editCategory,
        is_active: editIsActive,
      };

      await updateProduct(editingProduct.product_id, payload);
      setEditingProduct(null);
      onRefresh();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Product update failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search & Actions Bar */}
      <div className="bg-dukaan-card border border-dukaan-border rounded-2xl p-4 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-dukaan-muted">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search product ya alias..."
            className="w-full pl-9 pr-3.5 py-2 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl text-dukaan-text focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
          />
        </div>

        <button
          onClick={() => {
            setFormError(null);
            setShowAddModal(true);
          }}
          className="w-full sm:w-auto flex items-center justify-center gap-1.5 py-2 px-4 bg-dukaan-primary hover:bg-dukaan-primaryDark text-white font-bold text-xs rounded-xl shadow-xs transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Naya Product Jodein (Add Product)</span>
        </button>
      </div>

      {/* Products Table */}
      <div className="bg-dukaan-card border border-dukaan-border rounded-2xl shadow-warm overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-dukaan-border flex items-center justify-between">
          <h2 className="text-sm font-bold text-dukaan-text">
            Product Catalogue ({products.length})
          </h2>
          <span className="text-xs text-dukaan-muted">
            Dukaan Catalogue Management
          </span>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-xs text-dukaan-muted flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-dukaan-primary" />
            <span>Catalogue load ho raha hai...</span>
          </div>
        ) : products.length === 0 ? (
          <div className="p-12 text-center text-xs text-dukaan-muted">
            Koi product uplabdh nahi hai.
          </div>
        ) : (
          <div
            tabIndex={0}
            role="region"
            aria-label="Product catalogue table"
            className="overflow-x-auto"
          >
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-dukaan-canvas text-dukaan-muted uppercase text-[10px] font-bold tracking-wider border-b border-dukaan-border">
                <tr>
                  <th className="py-3 px-4">SKU / ID</th>
                  <th className="py-3 px-4">Product Name</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Unit / Pkg</th>
                  <th className="py-3 px-4">Kimat (Price)</th>
                  <th className="py-3 px-4">Sthiti (Active)</th>
                  <th className="py-3 px-4 text-right">Edit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dukaan-border/60">
                {products.map((p) => (
                  <tr
                    key={p.product_id}
                    className="hover:bg-dukaan-canvas/60 transition-colors"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-dukaan-text">
                      {p.product_id}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-dukaan-text">
                      <div>{p.name}</div>
                      {p.aliases && p.aliases.length > 0 && (
                        <div className="flex items-center gap-1 mt-0.5 text-[10px] text-dukaan-muted">
                          <Tag className="w-2.5 h-2.5" />
                          <span>{p.aliases.map((a) => a.alias_text).slice(0, 2).join(", ")}</span>
                        </div>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-dukaan-muted">
                      <span className="px-2 py-0.5 rounded-md bg-dukaan-canvas border border-dukaan-border text-[10px] font-medium">
                        {p.category}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-dukaan-muted">
                      {p.package_type} ({p.base_unit})
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-dukaan-text">
                      ₹{Number(p.price).toFixed(2)}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {p.is_active ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                          <CheckCircle className="w-3 h-3" />
                          Sakriya (Active)
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-stone-200 text-stone-700">
                          <XCircle className="w-3 h-3" />
                          Nishkriya
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => handleOpenEdit(p)}
                        className="inline-flex items-center gap-1 py-1 px-2.5 bg-dukaan-canvas hover:bg-dukaan-border border border-dukaan-border text-dukaan-text text-[11px] font-semibold rounded-lg transition-colors"
                      >
                        <Edit2 className="w-3 h-3 text-dukaan-muted" />
                        <span>Edit</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Product Modal */}
      {showAddModal && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4"
        >
          <div className="bg-dukaan-card border border-dukaan-border rounded-2xl p-6 max-w-lg w-full shadow-floating animate-in fade-in zoom-in-95 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-dukaan-text">
                Naya Product Catalogue Me Jodein (Add Product)
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-dukaan-muted hover:text-dukaan-text text-sm"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div
                role="alert"
                className="mb-4 p-3 rounded-xl bg-dukaan-errorBg border border-dukaan-error/30 flex items-start gap-2 text-xs text-dukaan-error"
              >
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSaveAdd} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-dukaan-text mb-1">
                  Product Name (नाम) *
                </label>
                <input
                  type="text"
                  required
                  value={addName}
                  onChange={(e) => setAddName(e.target.value)}
                  placeholder="e.g. Fortune Sunflower Oil 1L"
                  className="w-full py-2 px-3 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-dukaan-text mb-1">
                    Category (श्रेणी)
                  </label>
                  <select
                    value={addCategory}
                    onChange={(e) => setAddCategory(e.target.value)}
                    className="w-full py-2 px-3 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
                  >
                    <option value="Dairy">Dairy (दूध-दही)</option>
                    <option value="Staples">Staples (दाल-चावल-आटा)</option>
                    <option value="Snacks & Packaged Food">Snacks (नमकीन/बिस्किट)</option>
                    <option value="Beverages">Beverages (चाय/कॉफी/जूस)</option>
                    <option value="Personal Care">Personal Care</option>
                    <option value="Household Essentials">Household Essentials</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-dukaan-text mb-1">
                    Kimat / Price (₹) *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="1"
                    required
                    value={addPrice}
                    onChange={(e) => setAddPrice(e.target.value)}
                    placeholder="e.g. 150.00"
                    className="w-full py-2 px-3 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-dukaan-text mb-1">
                    Base Unit
                  </label>
                  <input
                    type="text"
                    value={addBaseUnit}
                    onChange={(e) => setAddBaseUnit(e.target.value)}
                    placeholder="piece, kg, litre"
                    className="w-full py-2 px-3 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-dukaan-text mb-1">
                    Package Type
                  </label>
                  <input
                    type="text"
                    value={addPackageType}
                    onChange={(e) => setAddPackageType(e.target.value)}
                    placeholder="packet, bottle, pouch"
                    className="w-full py-2 px-3 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-dukaan-text mb-1">
                    Initial Stock Qty
                  </label>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    value={addInitialStock}
                    onChange={(e) => setAddInitialStock(e.target.value)}
                    className="w-full py-2 px-3 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-dukaan-text mb-1">
                    Low Stock Threshold
                  </label>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    value={addLowStock}
                    onChange={(e) => setAddLowStock(e.target.value)}
                    className="w-full py-2 px-3 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-dukaan-text mb-1">
                  Aliases (Hindi / Hinglish Bol-Chal Ke Naam, comma separated)
                </label>
                <input
                  type="text"
                  value={addAliases}
                  onChange={(e) => setAddAliases(e.target.value)}
                  placeholder="e.g. fortune tel, meetha tel, cooking oil"
                  className="w-full py-2 px-3 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  disabled={isSubmitting}
                  className="py-2 px-3.5 text-xs font-semibold text-dukaan-muted hover:text-dukaan-text rounded-xl border border-dukaan-border"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex items-center gap-1.5 py-2 px-4 bg-dukaan-primary hover:bg-dukaan-primaryDark text-white font-bold text-xs rounded-xl shadow-xs disabled:opacity-50"
                >
                  {isSubmitting && <Loader2 className="w-3 h-3 animate-spin" />}
                  <span>Jodein (Save Product)</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Product Modal */}
      {editingProduct && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4"
        >
          <div className="bg-dukaan-card border border-dukaan-border rounded-2xl p-6 max-w-md w-full shadow-floating animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-bold text-dukaan-text">
                  Product Vivaran Badlein (Edit Product)
                </h3>
                <p className="text-xs text-dukaan-muted font-mono mt-0.5">
                  ID: {editingProduct.product_id}
                </p>
              </div>
              <button
                onClick={() => setEditingProduct(null)}
                className="text-dukaan-muted hover:text-dukaan-text text-sm"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div
                role="alert"
                className="mb-4 p-3 rounded-xl bg-dukaan-errorBg border border-dukaan-error/30 flex items-start gap-2 text-xs text-dukaan-error"
              >
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSaveEdit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-dukaan-text mb-1">
                  Product Name:
                </label>
                <input
                  type="text"
                  required
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full py-2 px-3 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-dukaan-text mb-1">
                  Kimat (Price ₹):
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="1"
                  required
                  value={editPrice}
                  onChange={(e) => setEditPrice(e.target.value)}
                  className="w-full py-2 px-3 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-dukaan-text mb-1">
                  Category:
                </label>
                <input
                  type="text"
                  value={editCategory}
                  onChange={(e) => setEditCategory(e.target.value)}
                  className="w-full py-2 px-3 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  id="edit-is-active"
                  type="checkbox"
                  checked={editIsActive}
                  onChange={(e) => setEditIsActive(e.target.checked)}
                  className="w-4 h-4 text-dukaan-primary rounded border-dukaan-border focus:ring-dukaan-primary/30"
                />
                <label htmlFor="edit-is-active" className="text-xs font-semibold text-dukaan-text cursor-pointer">
                  Product Dukan Par Sakriya (Active) Hai
                </label>
              </div>

              <div className="pt-3 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setEditingProduct(null)}
                  disabled={isSubmitting}
                  className="py-2 px-3.5 text-xs font-semibold text-dukaan-muted hover:text-dukaan-text rounded-xl border border-dukaan-border"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex items-center gap-1.5 py-2 px-4 bg-dukaan-primary hover:bg-dukaan-primaryDark text-white font-bold text-xs rounded-xl shadow-xs disabled:opacity-50"
                >
                  {isSubmitting && <Loader2 className="w-3 h-3 animate-spin" />}
                  <span>Save Karein</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
