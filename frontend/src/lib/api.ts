const API_BASE = '/api';

export interface Product {
	product: string;
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
	product: string;
	billing_unit: string;
	quantity: number;
	unit_price: number;
	total_price: number;
}

export interface Quote {
	id: string;
	name: string | null;
	billing_type: string;
	items: QuoteLineItem[];
	total: number;
	created_at: string;
	updated_at: string;
}

export interface SyncResponse {
	success: boolean;
	message: string;
	products_count: number;
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

export async function fetchProducts(region: string = 'us1'): Promise<Product[]> {
	const response = await fetch(`${API_BASE}/products?region=${region}`);
	if (!response.ok) throw new Error('Failed to fetch products');
	return response.json();
}

export async function fetchMetadata(region: string = 'us1'): Promise<PricingMetadata | null> {
	try {
		const response = await fetch(`${API_BASE}/pricing/metadata?region=${region}`);
		if (!response.ok) return null;
		return response.json();
	} catch {
		return null;
	}
}

export async function syncPricing(region: string = 'us1'): Promise<SyncResponse> {
	const response = await fetch(`${API_BASE}/pricing/sync?region=${region}`, { method: 'POST' });
	if (!response.ok) throw new Error('Failed to sync pricing');
	return response.json();
}

export async function createQuote(
	name: string | null,
	billing_type: string,
	items: { product: string; quantity: number }[]
): Promise<Quote> {
	const response = await fetch(`${API_BASE}/quotes`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ name, billing_type, items })
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
	billing_type: string,
	items: { product: string; quantity: number }[]
): Promise<Quote> {
	const response = await fetch(`${API_BASE}/quotes/${quoteId}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ name, billing_type, items })
	});
	if (!response.ok) throw new Error('Failed to update quote');
	return response.json();
}

