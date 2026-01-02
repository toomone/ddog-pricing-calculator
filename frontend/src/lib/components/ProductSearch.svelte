<script lang="ts">
	import { cn } from '$lib/utils';
	import { createEventDispatcher } from 'svelte';
	import type { Product } from '$lib/api';

	export let products: Product[] = [];
	export let selectedProduct: Product | null = null;
	export let placeholder: string = 'Search products...';
	export let id: string | undefined = undefined;

	let searchQuery = selectedProduct?.product || '';
	let isOpen = false;
	let isTyping = false; // Track if user is actively typing

	// Sync searchQuery when selectedProduct changes externally (but not while typing)
	$: if (selectedProduct && !isTyping) {
		searchQuery = selectedProduct.product;
	}
	// Clear search when selectedProduct is set to null externally
	$: if (!selectedProduct && !isTyping && searchQuery) {
		searchQuery = '';
	}
	let highlightedIndex = 0;
	let inputElement: HTMLInputElement;

	const dispatch = createEventDispatcher<{ select: Product }>();

	$: filteredProducts = searchQuery
		? products.filter((p) =>
				p.product.toLowerCase().includes(searchQuery.toLowerCase())
		  )
		: products;

	// Group products by category
	interface CategoryGroup {
		name: string;
		products: Product[];
	}
	
	$: groupedProducts = (() => {
		const groups: Record<string, Product[]> = {};
		for (const product of filteredProducts) {
			const category = product.category || 'Specific';
			if (!groups[category]) {
				groups[category] = [];
			}
			groups[category].push(product);
		}
		// Convert to array and maintain order (categories are already sorted in filteredProducts)
		const result: CategoryGroup[] = [];
		const seenCategories = new Set<string>();
		for (const product of filteredProducts) {
			const category = product.category || 'Specific';
			if (!seenCategories.has(category)) {
				seenCategories.add(category);
				result.push({ name: category, products: groups[category] });
			}
		}
		return result;
	})();

	// Flatten for keyboard navigation
	$: flatProducts = filteredProducts;

	$: if (filteredProducts.length > 0 && highlightedIndex >= filteredProducts.length) {
		highlightedIndex = 0;
	}

	function handleSelect(product: Product) {
		isTyping = false;
		selectedProduct = product;
		searchQuery = product.product;
		isOpen = false;
		dispatch('select', product);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (!isOpen && event.key === 'ArrowDown') {
			isOpen = true;
			return;
		}

		if (!isOpen) return;

		switch (event.key) {
			case 'ArrowDown':
				event.preventDefault();
				highlightedIndex = (highlightedIndex + 1) % filteredProducts.length;
				break;
			case 'ArrowUp':
				event.preventDefault();
				highlightedIndex =
					(highlightedIndex - 1 + filteredProducts.length) % filteredProducts.length;
				break;
			case 'Enter':
				event.preventDefault();
				if (filteredProducts[highlightedIndex]) {
					handleSelect(filteredProducts[highlightedIndex]);
				}
				break;
			case 'Escape':
				isOpen = false;
				break;
		}
	}

	function handleInput() {
		// User is actively typing
		isTyping = true;
		// Reopen dropdown when user types
		isOpen = true;
		// Clear selected product if search query doesn't match
		if (selectedProduct && searchQuery !== selectedProduct.product) {
			selectedProduct = null;
		}
	}

	function handleFocus() {
		isTyping = true;
		isOpen = true;
	}

	function handleBlur(event: FocusEvent) {
		// Delay to allow click on option
		setTimeout(() => {
			isOpen = false;
			isTyping = false;
		}, 150);
	}
</script>

<div class="relative w-full" {id}>
	<input
		bind:this={inputElement}
		type="text"
		{placeholder}
		bind:value={searchQuery}
		on:input={handleInput}
		on:focus={handleFocus}
		on:blur={handleBlur}
		on:keydown={handleKeydown}
		class={cn(
			'flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background',
			'placeholder:text-muted-foreground',
			'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:border-foreground/30',
			'transition-all duration-200'
		)}
	/>

	{#if isOpen && filteredProducts.length > 0}
		<div
			class="absolute z-[9999] mt-1 max-h-72 w-full overflow-auto rounded-lg border border-border bg-card p-1 shadow-2xl"
		>
			{#each groupedProducts as group}
				<!-- Category Header -->
				<div class="sticky top-0 z-10 bg-card px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground border-b border-border mb-1 shadow-sm">
					{group.name}
				</div>
				<!-- Products in this category -->
				{#each group.products as product}
					{@const index = flatProducts.indexOf(product)}
					<button
						type="button"
						class={cn(
							'relative flex w-full cursor-pointer select-none items-start rounded-md px-3 py-2 text-sm outline-none transition-colors text-left',
							index === highlightedIndex
								? 'bg-accent text-accent-foreground'
								: 'hover:bg-accent/50 hover:text-accent-foreground'
						)}
						on:mousedown|preventDefault={() => handleSelect(product)}
						on:mouseenter={() => (highlightedIndex = index)}
					>
						<div class="flex flex-col items-start gap-0.5 w-full">
							<span class="font-medium text-left">{product.product}</span>
							<span class="text-xs text-muted-foreground text-left">{product.billing_unit}</span>
						</div>
					</button>
				{/each}
			{/each}
		</div>
	{/if}

	{#if isOpen && searchQuery && filteredProducts.length === 0}
		<div
			class="absolute z-[9999] mt-1 w-full rounded-lg border border-border bg-card p-4 text-center text-sm text-muted-foreground shadow-2xl"
		>
			No products found
		</div>
	{/if}
</div>

