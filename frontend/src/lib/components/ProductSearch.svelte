<script lang="ts">
	import { cn } from '$lib/utils';
	import { createEventDispatcher } from 'svelte';
	import type { Product } from '$lib/api';

	export let products: Product[] = [];
	export let selectedProduct: Product | null = null;
	export let placeholder: string = 'Search products...';

	let searchQuery = '';
	let isOpen = false;
	let highlightedIndex = 0;
	let inputElement: HTMLInputElement;

	const dispatch = createEventDispatcher<{ select: Product }>();

	$: filteredProducts = searchQuery
		? products.filter((p) =>
				p.product.toLowerCase().includes(searchQuery.toLowerCase())
		  )
		: products;

	$: if (filteredProducts.length > 0 && highlightedIndex >= filteredProducts.length) {
		highlightedIndex = 0;
	}

	function handleSelect(product: Product) {
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
		// Reopen dropdown when user types
		isOpen = true;
		// Clear selected product if search query doesn't match
		if (selectedProduct && searchQuery !== selectedProduct.product) {
			selectedProduct = null;
		}
	}

	function handleFocus() {
		isOpen = true;
	}

	function handleBlur(event: FocusEvent) {
		// Delay to allow click on option
		setTimeout(() => {
			isOpen = false;
		}, 150);
	}
</script>

<div class="relative w-full">
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
			class="absolute z-[100] mt-1 max-h-60 w-full overflow-auto rounded-lg border border-border bg-card p-1 shadow-2xl"
		>
			{#each filteredProducts as product, index}
				<button
					type="button"
					class={cn(
						'relative flex w-full cursor-pointer select-none items-center rounded-md px-3 py-2 text-sm outline-none transition-colors',
						index === highlightedIndex
							? 'bg-accent text-accent-foreground'
							: 'hover:bg-accent/50 hover:text-accent-foreground'
					)}
					on:mousedown|preventDefault={() => handleSelect(product)}
					on:mouseenter={() => (highlightedIndex = index)}
				>
					<div class="flex flex-col items-start gap-0.5">
						<span class="font-medium">{product.product}</span>
						<span class="text-xs text-muted-foreground">{product.billing_unit}</span>
					</div>
				</button>
			{/each}
		</div>
	{/if}

	{#if isOpen && searchQuery && filteredProducts.length === 0}
		<div
			class="absolute z-[100] mt-1 w-full rounded-lg border border-border bg-card p-4 text-center text-sm text-muted-foreground shadow-2xl"
		>
			No products found
		</div>
	{/if}
</div>

