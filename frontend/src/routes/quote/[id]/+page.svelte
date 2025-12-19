<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { fetchQuote, type Quote } from '$lib/api';
	import { formatCurrency, formatNumber } from '$lib/utils';

	let quote: Quote | null = null;
	let loading = true;
	let error = '';
	let copied = false;

	// Region display names
	const regionNames: Record<string, string> = {
		'us': 'US (US1, US3, US5)',
		'us1-fed': 'US1-FED (GovCloud)',
		'eu1': 'EU1 (Europe)',
		'ap1': 'AP1 (Asia Pacific)',
		'ap2': 'AP2 (Asia Pacific 2)'
	};

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
		// Encode quote data as URL parameter for the main page (include product IDs and region)
		const cloneData = {
			name: quote.name,
			region: quote.region,
			items: quote.items.map(item => ({
				id: item.id,
				product: item.product,
				quantity: item.quantity
			}))
		};
		const encoded = encodeURIComponent(JSON.stringify(cloneData));
		goto(`/?clone=${encoded}`);
	}

	$: billingLabel =
		quote?.billing_type === 'annually'
			? 'Annual'
			: quote?.billing_type === 'monthly'
			? 'Monthly'
			: 'On-Demand';
	
	$: regionLabel = quote?.region ? (regionNames[quote.region] || quote.region.toUpperCase()) : 'US';
	
	// Calculate savings
	$: annualTotal = quote?.total_annually || 0;
	$: monthlyTotal = quote?.total_monthly || 0;
	$: onDemandTotal = quote?.total_on_demand || 0;
	
	$: savingsVsMonthly = monthlyTotal > annualTotal ? monthlyTotal - annualTotal : 0;
	$: savingsVsOnDemand = onDemandTotal > annualTotal ? onDemandTotal - annualTotal : 0;
	$: savingsPercentVsMonthly = monthlyTotal > 0 ? Math.round((savingsVsMonthly / monthlyTotal) * 100) : 0;
	$: savingsPercentVsOnDemand = onDemandTotal > 0 ? Math.round((savingsVsOnDemand / onDemandTotal) * 100) : 0;
</script>

<svelte:head>
	<title>{quote?.name || 'Quote'} | PriceHound</title>
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
		<Card class="mb-6 print:shadow-none print:border-0">
			<CardHeader class="pb-4">
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
					<div class="flex flex-wrap gap-2">
						<Badge variant="outline" class="text-sm">
							<svg class="mr-1 h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<circle cx="12" cy="12" r="10" />
								<path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
							</svg>
							{regionLabel}
						</Badge>
						<Badge class="text-sm bg-datadog-purple/10 text-datadog-purple border-datadog-purple/20">
							<svg class="mr-1 h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
								<line x1="16" y1="2" x2="16" y2="6" />
								<line x1="8" y1="2" x2="8" y2="6" />
								<line x1="3" y1="10" x2="21" y2="10" />
							</svg>
							{billingLabel} Billing
						</Badge>
					</div>
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
										{#if item.allotments && item.allotments.length > 0}
											<div class="mt-1 flex flex-wrap gap-1">
												{#each item.allotments as allot}
													<span class="inline-flex items-center rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
														+{formatNumber(allot.quantity_included)} {allot.allotted_product}
													</span>
												{/each}
											</div>
										{/if}
									</td>
									<td class="py-4 text-center font-mono">{formatNumber(item.quantity)}</td>
									<td class="py-4 text-right font-mono">{formatCurrency(item.unit_price)}</td>
									<td class="py-4 text-right font-mono font-semibold text-datadog-purple">
										{formatCurrency(item.total_price)}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
				
				<!-- Pricing Summary -->
				<div class="mt-6 rounded-lg border border-border bg-muted/30 p-4">
					<h3 class="mb-4 text-sm font-semibold text-muted-foreground uppercase tracking-wide">Pricing Summary</h3>
					
					<div class="grid gap-4 sm:grid-cols-3">
						<!-- Annual -->
						<div class="rounded-lg border border-datadog-green/30 bg-datadog-green/5 p-4 {quote.billing_type === 'annually' ? 'ring-2 ring-datadog-green' : ''}">
							<div class="flex items-center justify-between mb-2">
								<span class="text-sm font-medium text-muted-foreground">Annual</span>
								{#if quote.billing_type === 'annually'}
									<Badge class="bg-datadog-green text-white text-xs">Selected</Badge>
								{:else if savingsVsMonthly > 0 || savingsVsOnDemand > 0}
									<Badge variant="outline" class="text-datadog-green border-datadog-green text-xs">Best Value</Badge>
								{/if}
							</div>
							<div class="text-2xl font-bold text-datadog-green font-mono">
								{formatCurrency(annualTotal * 12)}<span class="text-sm font-normal text-muted-foreground">/yr</span>
							</div>
							<div class="text-sm text-muted-foreground font-mono">
								{formatCurrency(annualTotal)}/mo
							</div>
						</div>
						
						<!-- Monthly -->
						<div class="rounded-lg border border-border bg-card p-4 {quote.billing_type === 'monthly' ? 'ring-2 ring-datadog-blue' : ''}">
							<div class="flex items-center justify-between mb-2">
								<span class="text-sm font-medium text-muted-foreground">Monthly</span>
								{#if quote.billing_type === 'monthly'}
									<Badge class="bg-datadog-blue text-white text-xs">Selected</Badge>
								{/if}
							</div>
							<div class="text-2xl font-bold font-mono">
								{formatCurrency(monthlyTotal * 12)}<span class="text-sm font-normal text-muted-foreground">/yr</span>
							</div>
							<div class="text-sm text-muted-foreground font-mono">
								{formatCurrency(monthlyTotal)}/mo
							</div>
							{#if savingsVsMonthly > 0}
								<div class="mt-2 text-xs text-datadog-green">
									Save {formatCurrency(savingsVsMonthly * 12)}/yr ({savingsPercentVsMonthly}%) with annual
								</div>
							{/if}
						</div>
						
						<!-- On-Demand -->
						<div class="rounded-lg border border-border bg-card p-4 {quote.billing_type === 'on_demand' ? 'ring-2 ring-orange-500' : ''}">
							<div class="flex items-center justify-between mb-2">
								<span class="text-sm font-medium text-muted-foreground">On-Demand</span>
								{#if quote.billing_type === 'on_demand'}
									<Badge class="bg-orange-500 text-white text-xs">Selected</Badge>
								{/if}
							</div>
							<div class="text-2xl font-bold font-mono">
								{formatCurrency(onDemandTotal * 12)}<span class="text-sm font-normal text-muted-foreground">/yr</span>
							</div>
							<div class="text-sm text-muted-foreground font-mono">
								{formatCurrency(onDemandTotal)}/mo
							</div>
							{#if savingsVsOnDemand > 0}
								<div class="mt-2 text-xs text-datadog-green">
									Save {formatCurrency(savingsVsOnDemand * 12)}/yr ({savingsPercentVsOnDemand}%) with annual
								</div>
							{/if}
						</div>
					</div>
				</div>
			</CardContent>
		</Card>

		<!-- Actions -->
		<div class="flex flex-wrap items-center justify-center gap-3 print:hidden">
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
			<Button variant="outline" on:click={() => window.print()} class="gap-2">
				<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<polyline points="6 9 6 2 18 2 18 9" />
					<path d="M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2" />
					<rect x="6" y="14" width="12" height="8" />
				</svg>
				Print / PDF
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
	
	/* Print styles */
	@media print {
		:global(body) {
			background: white !important;
			-webkit-print-color-adjust: exact;
			print-color-adjust: exact;
		}
		
		:global(.container) {
			max-width: 100% !important;
			padding: 0 !important;
		}
	}
</style>

