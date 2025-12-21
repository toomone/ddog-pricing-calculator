const API_BASE = '/api';

export interface Product {
	id: string;
	product: string;
	plan: string; // 'Pro', 'Enterprise', or 'All'
	billing_unit: string;
	billed_annually: string | null;
	billed_month_to_month: string | null;
	on_demand: string | null;
}

export interface Region {
	name: string;
	url: string;
	site: string;
}

export interface RegionStatus {
	id: string;
	name: string;
	site: string;
	synced: boolean;
	last_sync: string | null;
	products_count: number;
}

export interface PricingMetadata {
	region: string;
	region_name: string;
	site: string;
	last_sync: string;
	products_count: number;
	source_url: string;
}

export interface QuoteLineItem {
	id?: string;
	product: string;
	billing_unit: string;
	quantity: number;
	unit_price: number;
	total_price: number;
	allotments?: { id?: string; allotted_product: string; quantity_included: number; allotted_unit: string }[];
}

export interface Quote {
	id: string;
	name: string | null;
	region: string;
	billing_type: string;
	items: QuoteLineItem[];
	total: number;
	total_annually: number | null;
	total_monthly: number | null;
	total_on_demand: number | null;
	created_at: string;
	updated_at: string;
	is_protected: boolean;
}

export interface SyncResponse {
	success: boolean;
	message: string;
	products_count: number;
}

export interface Allotment {
	parent_product: string;
	allotted_product: string;
	quantity_per_parent: number;
	allotted_unit: string;
	per_parent_unit: string;
	frequency: string;
	parent_product_id?: string;
	allotted_product_id?: string;
}

export async function fetchRegions(): Promise<Record<string, Region>> {
	const response = await fetch(`${API_BASE}/regions`);
	if (!response.ok) throw new Error('Failed to fetch regions');
	return response.json();
}

export async function fetchRegionsStatus(): Promise<RegionStatus[]> {
	const response = await fetch(`${API_BASE}/regions/status`);
	if (!response.ok) throw new Error('Failed to fetch regions status');
	return response.json();
}

export async function fetchProducts(region: string = 'us'): Promise<Product[]> {
	const response = await fetch(`${API_BASE}/products?region=${region}`);
	if (!response.ok) throw new Error('Failed to fetch products');
	return response.json();
}

export async function fetchMetadata(region: string = 'us'): Promise<PricingMetadata | null> {
	try {
		const response = await fetch(`${API_BASE}/pricing/metadata?region=${region}`);
		if (!response.ok) return null;
		return response.json();
	} catch {
		return null;
	}
}

export async function syncPricing(region: string = 'us'): Promise<SyncResponse> {
	const response = await fetch(`${API_BASE}/pricing/sync?region=${region}`, { method: 'POST' });
	if (!response.ok) throw new Error('Failed to sync pricing');
	return response.json();
}

export async function syncAllPricing(): Promise<{ results: SyncResponse[] }> {
	const response = await fetch(`${API_BASE}/pricing/sync-all`, { method: 'POST' });
	if (!response.ok) throw new Error('Failed to sync all pricing');
	return response.json();
}

export async function createQuote(
	name: string | null,
	region: string,
	billing_type: string,
	items: { id?: string; product: string; quantity: number; allotments?: { id?: string; allotted_product: string; quantity_included: number; allotted_unit: string }[] }[],
	edit_password?: string | null
): Promise<Quote> {
	const response = await fetch(`${API_BASE}/quotes`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ name, region, billing_type, items, edit_password: edit_password || null })
	});
	if (!response.ok) throw new Error('Failed to create quote');
	return response.json();
}

export async function fetchQuote(quoteId: string): Promise<Quote> {
	const response = await fetch(`${API_BASE}/quotes/${quoteId}`);
	if (!response.ok) throw new Error('Quote not found');
	return response.json();
}

export async function updateQuote(
	quoteId: string,
	name: string | null,
	region: string,
	billing_type: string,
	items: { id?: string; product: string; quantity: number; allotments?: { id?: string; allotted_product: string; quantity_included: number; allotted_unit: string }[] }[],
	edit_password?: string | null
): Promise<Quote> {
	const response = await fetch(`${API_BASE}/quotes/${quoteId}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ name, region, billing_type, items, edit_password: edit_password || null })
	});
	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Failed to update quote' }));
		throw new Error(error.detail || 'Failed to update quote');
	}
	return response.json();
}

export async function verifyQuotePassword(quoteId: string, password: string): Promise<{ valid: boolean; message: string }> {
	const response = await fetch(`${API_BASE}/quotes/${quoteId}/verify-password`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ password })
	});
	if (!response.ok) {
		if (response.status === 404) throw new Error('Quote not found');
		throw new Error('Failed to verify password');
	}
	return response.json();
}

export async function fetchAllotments(): Promise<Allotment[]> {
	const response = await fetch(`${API_BASE}/allotments`);
	if (!response.ok) throw new Error('Failed to fetch allotments');
	return response.json();
}

export async function fetchProductAllotments(productName: string): Promise<Allotment[]> {
	const response = await fetch(`${API_BASE}/allotments/product/${encodeURIComponent(productName)}`);
	if (!response.ok) throw new Error('Failed to fetch product allotments');
	return response.json();
}

export async function initAllotments(): Promise<{ success: boolean; message: string }> {
	const response = await fetch(`${API_BASE}/allotments/init`, { method: 'POST' });
	if (!response.ok) throw new Error('Failed to initialize allotments');
	return response.json();
}

