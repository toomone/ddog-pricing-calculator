<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import ProductSearch from './ProductSearch.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { formatCurrency, parsePrice, formatNumber, isPercentagePrice, parsePercentage } from '$lib/utils';
	import type { Product, Allotment } from '$lib/api';

	interface AllotmentItem {
		product: Product | null;
		includedQuantity: number;
		allotmentInfo: Allotment | null;
	}

	export let products: Product[] = [];
	export let selectedProduct: Product | null = null;
	export let quantity: number = 1;
	export let index: number = 0;
	export let showAnnual: boolean = true;
	export let showMonthly: boolean = true;
	export let showOnDemand: boolean = true;
	export let isAllotment: boolean = false;
	export let includedQuantity: number = 0;
	export let allotmentInfo: Allotment | null = null;
	export let totalAllottedForProduct: number = 0; // Total included from parent products
	export let lineAllotments: AllotmentItem[] = []; // Allotments for this line

	const dispatch = createEventDispatcher<{
		update: { product: Product | null; quantity: number };
		remove: void;
	}>();

	// Check if this product uses percentage-based pricing
	$: isPercentageBased = selectedProduct ? isPercentagePrice(selectedProduct.billed_annually) : false;

	// Calculate all 3 prices (or percentages)
	$: annualPrice = selectedProduct ? parsePrice(selectedProduct.billed_annually) : 0;
	$: monthlyPrice = selectedProduct ? parsePrice(selectedProduct.billed_month_to_month) : 0;
	$: onDemandPrice = selectedProduct ? parsePrice(selectedProduct.on_demand) : 0;

	// For percentage-based pricing, get the percentage values
	$: annualPercent = selectedProduct ? parsePercentage(selectedProduct.billed_annually) : 0;
	$: monthlyPercent = selectedProduct ? parsePercentage(selectedProduct.billed_month_to_month) : 0;
	$: onDemandPercent = selectedProduct ? parsePercentage(selectedProduct.on_demand) : 0;

	// For allotments, only charge for quantity exceeding the included amount
	$: chargeableQuantity = isAllotment ? Math.max(0, quantity - includedQuantity) : quantity;

	// Calculate totals for all 3 (only for chargeable quantity)
	// For percentage items, the "total" shown is just the percentage - actual calculation done in summary
	$: annualTotal = isPercentageBased ? annualPercent : annualPrice * chargeableQuantity;
	$: monthlyTotal = isPercentageBased ? monthlyPercent : monthlyPrice * chargeableQuantity;
	$: onDemandTotal = isPercentageBased ? onDemandPercent : onDemandPrice * chargeableQuantity;

	$: visibleColumns = [showAnnual, showMonthly, showOnDemand].filter(Boolean).length;

	// Abbreviate common unit names
	const unitAbbreviations: Record<string, string> = {
		'investigations': 'invest.',
		'investigation': 'invest.',
		'containers': 'cont.',
		'container': 'cont.',
		'metrics': 'metrics',
		'metric': 'metric',
		'sessions': 'sess.',
		'session': 'sess.',
		'executions': 'exec.',
		'execution': 'exec.',
		'requests': 'req.',
		'request': 'req.',
		'invocations': 'invoc.',
		'invocation': 'invoc.',
		'events': 'events',
		'event': 'event',
		'spans': 'spans',
		'span': 'span',
		'queries': 'queries',
		'query': 'query',
		'hosts': 'hosts',
		'host': 'host',
		'functions': 'func.',
		'function': 'func.',
		'indexed spans': 'idx spans',
		'ingested spans': 'ing. spans',
		'indexed logs': 'idx logs',
		'ingested logs': 'ing. logs',
		'custom metrics': 'cust. metrics',
		'custom events': 'cust. events',
		'profiled hosts': 'prof. hosts',
		'profiled containers': 'prof. cont.',
		'normalized queries': 'norm. queries',
		'active users': 'users',
		'browser sessions': 'br. sess.',
		'mobile sessions': 'mob. sess.',
		'replay sessions': 'replay sess.',
		'test runs': 'tests',
		'pipeline executions': 'pipelines'
	};

	function abbreviateUnit(unit: string): string {
		const lowerUnit = unit.toLowerCase();
		// Check for exact matches first
		if (unitAbbreviations[lowerUnit]) {
			return unitAbbreviations[lowerUnit];
		}
		// Check for partial matches
		for (const [key, abbr] of Object.entries(unitAbbreviations)) {
			if (lowerUnit.includes(key)) {
				return lowerUnit.replace(key, abbr);
			}
		}
		// Truncate long unit names
		if (unit.length > 10) {
			return unit.substring(0, 8) + '.';
		}
		return unit;
	}

	// Extract period from billing unit (per month, per hour, etc.)
	function extractPeriod(billingUnit: string): string {
		const lowerUnit = billingUnit.toLowerCase();
		if (lowerUnit.includes('per month') || lowerUnit.includes('/month')) return '/mo';
		if (lowerUnit.includes('per hour') || lowerUnit.includes('/hour')) return '/hr';
		if (lowerUnit.includes('per day') || lowerUnit.includes('/day')) return '/day';
		if (lowerUnit.includes('per year') || lowerUnit.includes('/year')) return '/yr';
		return '';
	}

	// Extract multiplier and unit from billing_unit (e.g., "per 20 investigations" → { multiplier: 20, unit: "investigations" })
	function parseBillingUnit(billingUnit: string): { multiplier: number; unit: string; period: string } | null {
		if (!billingUnit) return null;
		
		const period = extractPeriod(billingUnit);
		
		// Match patterns like "per 20 investigations", "per 100 metrics per month"
		const match = billingUnit.match(/per\s+([\d,]+)\s+([a-zA-Z\s]+?)(?:\s+per\s+|$)/i);
		if (match) {
			const multiplier = parseInt(match[1].replace(/,/g, ''), 10);
			const unit = match[2].trim();
			if (multiplier > 1) {
				return { multiplier, unit: abbreviateUnit(unit), period };
			}
		}
		return null;
	}

	$: billingUnitInfo = selectedProduct ? parseBillingUnit(selectedProduct.billing_unit) : null;
	$: totalUnits = billingUnitInfo ? quantity * billingUnitInfo.multiplier : null;

	function handleProductSelect(event: CustomEvent<Product>) {
		selectedProduct = event.detail;
		dispatch('update', { product: selectedProduct, quantity });
	}

	function handleQuantityChange() {
		dispatch('update', { product: selectedProduct, quantity });
	}

	function handleRemove() {
		dispatch('remove');
	}
</script>

{#if isAllotment}
	<!-- Compact Allotment Line (read-only) -->
	<div
		class="relative rounded-lg border border-datadog-green/20 bg-datadog-green/5 px-4 py-2 ml-8"
		style="animation: slideIn 0.3s ease-out {index * 0.05}s both;"
	>
		<div class="absolute -left-6 top-1/2 -translate-y-1/2 text-datadog-green/50">
			<svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M9 18l6-6-6-6" />
			</svg>
		</div>

		<div class="flex items-center gap-4">
			<!-- Product Name -->
			<div class="flex-1 min-w-0 flex items-center gap-2">
				<span class="text-sm text-muted-foreground truncate">
					{selectedProduct?.product || 'Unknown product'}
				</span>
				<Badge variant="outline" class="text-[9px] px-1.5 py-0 bg-datadog-green/10 text-datadog-green border-datadog-green/30 shrink-0">
					Allotment
				</Badge>
			</div>

			<!-- Included Quantity -->
			<div class="text-xs text-muted-foreground shrink-0">
				{formatNumber(includedQuantity)} {allotmentInfo?.allotted_unit || 'units'}
			</div>
		</div>
	</div>
{:else}
	<!-- Regular Product Line -->
	<div
		class="group relative rounded-xl border border-border/50 bg-card/50 p-4 transition-all hover:border-foreground/20 hover:bg-card/80"
		style="animation: slideIn 0.3s ease-out {index * 0.05}s both;"
	>
		<div class="flex flex-col gap-4 lg:flex-row lg:items-start">
			<!-- Product Search -->
			<div class="flex-1 min-w-0">
				<div class="mb-1.5 h-4"></div>
				<ProductSearch {products} {selectedProduct} on:select={handleProductSelect} />
				{#if selectedProduct}
					<Badge variant="outline" class="mt-2 text-xs">
						{selectedProduct.billing_unit}
					</Badge>
				{/if}
			</div>

			<!-- Quantity -->
			<div class="w-28 shrink-0">
				<div class="mb-1.5 h-4"></div>
				<input
					type="number"
					min="1"
					bind:value={quantity}
					on:change={handleQuantityChange}
					class="flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-center font-mono ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200"
				/>
				{#if totalUnits !== null && billingUnitInfo}
					<div class="mt-1 text-[10px] text-center text-muted-foreground font-mono">
						= {formatNumber(totalUnits)} {billingUnitInfo.unit}{billingUnitInfo.period}
					</div>
				{/if}
				{#if totalAllottedForProduct > 0}
					<div class="mt-1 text-[10px] text-center text-datadog-green">
						+ {formatNumber(totalAllottedForProduct)} included
					</div>
				{/if}
			</div>

			<!-- Price Columns -->
			<div class="flex gap-2" style="width: {visibleColumns * 110}px;">
				{#if showAnnual}
					<div class="flex-1 text-center min-w-[100px]">
						<label class="mb-1.5 block text-xs font-medium text-datadog-green">Annually</label>
						<div class="rounded-lg bg-datadog-green/10 border border-datadog-green/20 px-2 py-2">
							<div class="font-mono text-sm font-semibold text-datadog-green truncate">
								{#if !selectedProduct}
									-
								{:else if isPercentageBased}
									{annualPercent}%
								{:else}
									{formatCurrency(annualTotal)}
								{/if}
							</div>
							{#if selectedProduct && !isPercentageBased && annualPrice > 0}
								<div class="font-mono text-[10px] text-datadog-green/60 mt-0.5">
									{formatCurrency(annualPrice)}/unit
								</div>
							{:else if selectedProduct && isPercentageBased}
								<div class="font-mono text-[10px] text-datadog-green/60 mt-0.5">
									of total
								</div>
							{/if}
						</div>
					</div>
				{/if}

				{#if showMonthly}
					<div class="flex-1 text-center min-w-[100px]">
						<label class="mb-1.5 block text-xs font-medium text-datadog-blue">Monthly</label>
						<div class="rounded-lg bg-datadog-blue/10 border border-datadog-blue/20 px-2 py-2">
							<div class="font-mono text-sm font-semibold text-datadog-blue truncate">
								{#if !selectedProduct}
									-
								{:else if isPercentageBased}
									{monthlyPercent}%
								{:else}
									{formatCurrency(monthlyTotal)}
								{/if}
							</div>
							{#if selectedProduct && !isPercentageBased && monthlyPrice > 0}
								<div class="font-mono text-[10px] text-datadog-blue/60 mt-0.5">
									{formatCurrency(monthlyPrice)}/unit
								</div>
							{:else if selectedProduct && isPercentageBased}
								<div class="font-mono text-[10px] text-datadog-blue/60 mt-0.5">
									of total
								</div>
							{/if}
						</div>
					</div>
				{/if}

				{#if showOnDemand}
					<div class="flex-1 text-center min-w-[100px]">
						<label class="mb-1.5 block text-xs font-medium text-datadog-orange">On-Demand</label>
						<div class="rounded-lg bg-datadog-orange/10 border border-datadog-orange/20 px-2 py-2">
							<div class="font-mono text-sm font-semibold text-datadog-orange truncate">
								{#if !selectedProduct}
									-
								{:else if isPercentageBased}
									{onDemandPercent}%
								{:else}
									{formatCurrency(onDemandTotal)}
								{/if}
							</div>
							{#if selectedProduct && !isPercentageBased && onDemandPrice > 0}
								<div class="font-mono text-[10px] text-datadog-orange/60 mt-0.5">
									{formatCurrency(onDemandPrice)}/unit
								</div>
							{:else if selectedProduct && isPercentageBased}
								<div class="font-mono text-[10px] text-datadog-orange/60 mt-0.5">
									of total
								</div>
							{/if}
						</div>
					</div>
				{/if}
			</div>

			<!-- Remove Button -->
			<div class="absolute -right-2 -top-2 lg:relative lg:right-auto lg:top-auto lg:self-center lg:ml-2">
				<div class="mb-1.5 h-4 hidden lg:block"></div>
				<Button
					variant="ghost"
					size="icon"
					class="h-8 w-8 rounded-full text-muted-foreground/40 transition-all hover:bg-destructive hover:text-white group-hover:bg-destructive/10 group-hover:text-destructive"
					on:click={handleRemove}
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2M10 11v6M14 11v6" />
					</svg>
				</Button>
			</div>
		</div>

		<!-- Included Allotments (inside product card) -->
		{#if lineAllotments.length > 0}
			<div class="mt-3 pt-3 border-t border-border/30">
				<div class="flex items-center gap-2 mb-1.5">
					<svg class="w-3.5 h-3.5 text-muted-foreground/70" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					<span class="text-[10px] font-medium text-muted-foreground/70 uppercase tracking-wide">Included Allotments</span>
				</div>
				<ul class="space-y-0.5 pl-5">
					{#each lineAllotments as allotment}
						<li class="flex items-center gap-2 text-xs text-muted-foreground">
							<span class="w-1 h-1 rounded-full bg-muted-foreground/40"></span>
							<span class="truncate">{allotment.product?.product || 'Unknown'}</span>
							<span class="ml-auto font-mono text-[10px] text-muted-foreground/70 shrink-0">
								{formatNumber(allotment.includedQuantity || 0)} {allotment.allotmentInfo?.allotted_unit || 'units'}
							</span>
						</li>
					{/each}
				</ul>
			</div>
		{/if}
	</div>
{/if}

<style>
	@keyframes slideIn {
		from {
			opacity: 0;
			transform: translateY(-10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
