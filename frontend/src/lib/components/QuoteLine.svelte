<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import ProductSearch from './ProductSearch.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { formatCurrency, parsePrice } from '$lib/utils';
	import type { Product } from '$lib/api';

	export let products: Product[] = [];
	export let selectedProduct: Product | null = null;
	export let quantity: number = 1;
	export let index: number = 0;
	export let showAnnual: boolean = true;
	export let showMonthly: boolean = true;
	export let showOnDemand: boolean = true;

	const dispatch = createEventDispatcher<{
		update: { product: Product | null; quantity: number };
		remove: void;
	}>();

	// Calculate all 3 prices
	$: annualPrice = selectedProduct ? parsePrice(selectedProduct.billed_annually) : 0;
	$: monthlyPrice = selectedProduct ? parsePrice(selectedProduct.billed_month_to_month) : 0;
	$: onDemandPrice = selectedProduct ? parsePrice(selectedProduct.on_demand) : 0;

	// Calculate totals for all 3
	$: annualTotal = annualPrice * quantity;
	$: monthlyTotal = monthlyPrice * quantity;
	$: onDemandTotal = onDemandPrice * quantity;

	$: visibleColumns = [showAnnual, showMonthly, showOnDemand].filter(Boolean).length;

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

<div
	class="group relative rounded-xl border border-border/50 bg-card/50 p-4 transition-all hover:border-datadog-purple/30 hover:bg-card/80"
	style="animation: slideIn 0.3s ease-out {index * 0.05}s both;"
>
	<div class="flex flex-col gap-4 lg:flex-row lg:items-start">
		<!-- Product Search -->
		<div class="flex-1 min-w-0">
			<label class="mb-1.5 block text-xs font-medium text-muted-foreground">Product</label>
			<ProductSearch {products} {selectedProduct} on:select={handleProductSelect} />
			{#if selectedProduct}
				<Badge variant="outline" class="mt-2 text-xs">
					{selectedProduct.billing_unit}
				</Badge>
			{/if}
		</div>

		<!-- Quantity -->
		<div class="w-20 shrink-0">
			<label class="mb-1.5 block text-xs font-medium text-muted-foreground">Qty</label>
			<input
				type="number"
				min="1"
				bind:value={quantity}
				on:change={handleQuantityChange}
				class="flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-center font-mono ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-datadog-purple focus-visible:ring-offset-2 focus-visible:border-datadog-purple disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200"
			/>
		</div>

		<!-- Price Columns - Dynamic based on visibility -->
		<div class="flex gap-2" style="width: {visibleColumns * 110}px;">
			{#if showAnnual}
				<div class="flex-1 text-center min-w-[100px]">
					<label class="mb-1.5 block text-xs font-medium text-datadog-green">Annual</label>
					<div class="rounded-lg bg-datadog-green/10 border border-datadog-green/20 px-2 py-2">
						<div class="font-mono text-sm font-semibold text-datadog-green truncate">
							{selectedProduct ? formatCurrency(annualTotal) : '-'}
						</div>
						{#if selectedProduct && annualPrice > 0}
							<div class="text-[10px] text-muted-foreground mt-0.5 truncate">
								{formatCurrency(annualPrice)}/ea
							</div>
						{/if}
					</div>
				</div>
			{/if}

			{#if showMonthly}
				<div class="flex-1 text-center min-w-[100px]">
					<label class="mb-1.5 block text-xs font-medium text-datadog-purple">Monthly</label>
					<div class="rounded-lg bg-datadog-purple/10 border border-datadog-purple/20 px-2 py-2">
						<div class="font-mono text-sm font-semibold text-datadog-purple truncate">
							{selectedProduct ? formatCurrency(monthlyTotal) : '-'}
						</div>
						{#if selectedProduct && monthlyPrice > 0}
							<div class="text-[10px] text-muted-foreground mt-0.5 truncate">
								{formatCurrency(monthlyPrice)}/ea
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
							{selectedProduct ? formatCurrency(onDemandTotal) : '-'}
						</div>
						{#if selectedProduct && onDemandPrice > 0}
							<div class="text-[10px] text-muted-foreground mt-0.5 truncate">
								{formatCurrency(onDemandPrice)}/ea
							</div>
						{/if}
					</div>
				</div>
			{/if}
		</div>

		<!-- Remove Button -->
		<div class="absolute -right-2 -top-2 lg:relative lg:right-auto lg:top-auto lg:self-center lg:ml-2">
			<Button
				variant="ghost"
				size="icon"
				class="h-8 w-8 rounded-full bg-destructive/10 text-destructive opacity-0 transition-opacity group-hover:opacity-100 hover:bg-destructive hover:text-white"
				on:click={handleRemove}
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2M10 11v6M14 11v6" />
				</svg>
			</Button>
		</div>
	</div>
</div>

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
