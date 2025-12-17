<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { fetchQuote, type Quote } from '$lib/api';
	import { formatCurrency } from '$lib/utils';

	let quote: Quote | null = null;
	let loading = true;
	let error = '';
	let copied = false;

	$: quoteId = $page.params.id;

	onMount(async () => {
		await loadQuote();
	});

	async function loadQuote() {
		loading = true;
		error = '';
		try {
			quote = await fetchQuote(quoteId);
		} catch (e) {
			error = 'Quote not found or has expired';
		} finally {
			loading = false;
		}
	}

	function copyUrl() {
		navigator.clipboard.writeText(window.location.href);
		copied = true;
		setTimeout(() => copied = false, 2000);
	}

	function cloneQuote() {
		if (!quote) return;
		// Encode quote data as URL parameter for the main page
		const cloneData = {
			name: quote.name,
			items: quote.items.map(item => ({
				product: item.product,
				quantity: item.quantity
			}))
		};
		const encoded = encodeURIComponent(JSON.stringify(cloneData));
		goto(`/?clone=${encoded}`);
	}

	$: billingLabel =
		quote?.billing_type === 'annually'
			? 'Annual billing'
			: quote?.billing_type === 'monthly'
			? 'Monthly billing'
			: 'On-demand';
</script>

<svelte:head>
	<title>{quote?.name || 'Quote'} | Datadog Pricing Calculator</title>
</svelte:head>

<div class="container mx-auto max-w-4xl px-4 py-8">
	<!-- Header -->
	<header class="mb-8">
		<a href="/" class="mb-4 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-datadog-purple">
			<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M19 12H5M12 19l-7-7 7-7" />
			</svg>
			Back to Calculator
		</a>
		<div class="flex items-center gap-3">
			<div class="flex h-10 w-10 items-center justify-center rounded-lg bg-datadog-purple shadow-lg shadow-datadog-purple/25">
				<svg class="h-5 w-5 text-white" viewBox="0 0 24 24" fill="currentColor">
					<path d="M12.13 2C6.54 2 2 6.54 2 12.13c0 5.59 4.54 10.13 10.13 10.13 5.59 0 10.13-4.54 10.13-10.13C22.26 6.54 17.72 2 12.13 2zm5.41 14.35c-.31.31-.82.31-1.13 0l-3.07-3.07-1.17 1.17 3.07 3.07c.31.31.31.82 0 1.13-.31.31-.82.31-1.13 0l-3.07-3.07-1.93 1.93c-.31.31-.82.31-1.13 0-.31-.31-.31-.82 0-1.13l1.93-1.93-3.07-3.07c-.31-.31-.31-.82 0-1.13.31-.31.82-.31 1.13 0l3.07 3.07 1.17-1.17-3.07-3.07c-.31-.31-.31-.82 0-1.13.31-.31.82-.31 1.13 0l3.07 3.07 1.93-1.93c.31-.31.82-.31 1.13 0 .31.31.31.82 0 1.13l-1.93 1.93 3.07 3.07c.31.31.31.82 0 1.13z"/>
				</svg>
			</div>
			<h1 class="text-2xl font-bold tracking-tight">Shared Quote</h1>
		</div>
	</header>

	{#if loading}
		<div class="flex items-center justify-center py-24">
			<svg class="h-10 w-10 animate-spin text-datadog-purple" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M21 12a9 9 0 11-6.219-8.56" />
			</svg>
		</div>
	{:else if error}
		<Card class="text-center">
			<CardContent class="py-12">
				<svg class="mx-auto mb-4 h-16 w-16 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
					<circle cx="12" cy="12" r="10" />
					<path d="M12 8v4M12 16h.01" />
				</svg>
				<h2 class="mb-2 text-xl font-semibold">Quote Not Found</h2>
				<p class="mb-6 text-muted-foreground">{error}</p>
				<Button href="/">Create New Quote</Button>
			</CardContent>
		</Card>
	{:else if quote}
		<Card class="mb-6">
			<CardHeader>
				<div class="flex flex-wrap items-start justify-between gap-4">
					<div>
						<CardTitle class="text-2xl">{quote.name}</CardTitle>
						<CardDescription>
							Created {new Date(quote.created_at).toLocaleDateString('en-US', {
								year: 'numeric',
								month: 'long',
								day: 'numeric'
							})}
						</CardDescription>
					</div>
					<Badge variant="outline" class="text-sm">{billingLabel}</Badge>
				</div>
			</CardHeader>
			<CardContent>
				<!-- Items Table -->
				<div class="overflow-x-auto">
					<table class="w-full">
						<thead>
							<tr class="border-b-2 border-border text-left text-sm text-muted-foreground">
								<th class="pb-3 font-medium">Product</th>
								<th class="pb-3 text-center font-medium">Qty</th>
								<th class="pb-3 text-right font-medium">Unit Price</th>
								<th class="pb-3 text-right font-medium">Total</th>
							</tr>
						</thead>
						<tbody>
							{#each quote.items as item, index}
								<tr
									class="border-b border-border/50"
									style="animation: fadeIn 0.3s ease-out {index * 0.05}s both;"
								>
									<td class="py-4">
										<div class="font-medium">{item.product}</div>
										<div class="text-xs text-muted-foreground">{item.billing_unit}</div>
									</td>
									<td class="py-4 text-center font-mono">{item.quantity}</td>
									<td class="py-4 text-right font-mono">{formatCurrency(item.unit_price)}</td>
									<td class="py-4 text-right font-mono font-semibold text-datadog-purple">
										{formatCurrency(item.total_price)}
									</td>
								</tr>
							{/each}
						</tbody>
						<tfoot>
							<tr>
								<td colspan="3" class="pt-4 text-right font-semibold">Annual Total</td>
								<td class="pt-4 text-right text-2xl font-bold text-datadog-green">
									{formatCurrency(quote.total * 12)}
								</td>
							</tr>
							<tr>
								<td colspan="3" class="pt-1 text-right text-sm text-muted-foreground">Monthly Cost</td>
								<td class="pt-1 text-right font-mono text-muted-foreground">
									{formatCurrency(quote.total)}/mo
								</td>
							</tr>
						</tfoot>
					</table>
				</div>
			</CardContent>
		</Card>

		<!-- Actions -->
		<div class="flex flex-wrap items-center justify-center gap-3">
			<Button variant="outline" on:click={copyUrl} class="gap-2">
				{#if copied}
					<svg class="h-4 w-4 text-datadog-green" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M20 6L9 17l-5-5" />
					</svg>
					Copied!
				{:else}
					<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<rect x="9" y="9" width="13" height="13" rx="2" />
						<path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
					</svg>
					Copy Link
				{/if}
			</Button>
			<Button on:click={cloneQuote} class="gap-2 bg-datadog-purple hover:bg-datadog-purple/90">
				<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
					<path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
				</svg>
				Clone & Edit
			</Button>
			<Button variant="outline" href="/" class="gap-2">
				<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M12 5v14M5 12h14" />
				</svg>
				New Quote
			</Button>
		</div>
	{/if}
</div>

<style>
	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateX(-10px);
		}
		to {
			opacity: 1;
			transform: translateX(0);
		}
	}
</style>

