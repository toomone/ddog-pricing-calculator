<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Input } from '$lib/components/ui/input';
	import { fetchQuote, verifyQuotePassword, type Quote } from '$lib/api';
	import { formatCurrency, formatNumber } from '$lib/utils';

	let quote: Quote | null = null;
	let loading = true;
	let error = '';
	let copied = false;
	let tierMenuOpen = false;
	
	// Password protection
	let passwordModalOpen = false;
	let editPassword = '';
	let passwordError = '';
	let verifying = false;
	let isUnlocked = false;
	
	// Single tier selection (annual, monthly, on-demand)
	let selectedTier: 'annual' | 'monthly' | 'on-demand' = 'annual';
	
	$: tierLabel = selectedTier === 'annual' ? 'Annually' : selectedTier === 'monthly' ? 'Monthly' : 'On-Demand';
	$: tierColor = selectedTier === 'annual' ? 'datadog-green' : selectedTier === 'monthly' ? 'datadog-blue' : 'datadog-orange';

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

	function attemptEdit() {
		if (!quote) return;
		
		if (quote.is_protected && !isUnlocked) {
			// Show password modal
			passwordModalOpen = true;
			editPassword = '';
			passwordError = '';
		} else {
			// Redirect to editor directly
			redirectToEditor();
		}
	}

	async function verifyAndUnlock() {
		if (!quote) return;
		
		verifying = true;
		passwordError = '';
		
		try {
			const result = await verifyQuotePassword(quoteId, editPassword);
			if (result.valid) {
				isUnlocked = true;
				passwordModalOpen = false;
				// Redirect to editor with quote data and password
				redirectToEditor();
			} else {
				passwordError = result.message || 'Invalid password';
			}
		} catch (e) {
			passwordError = 'Failed to verify password';
		} finally {
			verifying = false;
		}
	}

	function redirectToEditor() {
		if (!quote) return;
		// Encode quote data for the editor, include the quote ID and password for saving
		const editData = {
			quoteId: quote.id,
			name: quote.name,
			region: quote.region,
			editPassword: isUnlocked ? editPassword : null,
			items: quote.items.map(item => ({
				id: item.id,
				product: item.product,
				quantity: item.quantity
			}))
		};
		const encoded = encodeURIComponent(JSON.stringify(editData));
		goto(`/?edit=${encoded}`);
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

<svelte:window on:click={() => tierMenuOpen = false} />

<div class="container mx-auto max-w-4xl px-4 py-8">
	<!-- Header -->
	<header class="mb-8">
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
						{#if quote.is_protected}
							<Badge variant="outline" class="text-sm {isUnlocked ? 'text-datadog-green border-datadog-green/50' : 'text-muted-foreground'}">
								<svg class="mr-1 h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									{#if isUnlocked}
										<rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
										<path d="M7 11V7a5 5 0 019.9-1" />
									{:else}
										<rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
										<path d="M7 11V7a5 5 0 0110 0v4" />
									{/if}
								</svg>
								{isUnlocked ? 'Unlocked' : 'Protected'}
							</Badge>
						{/if}
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
					
					{#if selectedTier === 'annual'}
						<!-- Annual -->
						<div class="rounded-lg border-2 border-datadog-green/50 bg-datadog-green/5 p-6">
							<div class="flex items-center justify-between mb-3">
								<span class="text-lg font-semibold text-datadog-green">Billed Annually</span>
								{#if savingsVsMonthly > 0 || savingsVsOnDemand > 0}
									<Badge class="bg-datadog-green text-white text-xs">Best Value</Badge>
								{/if}
							</div>
							<div class="text-4xl font-bold text-datadog-green font-mono mb-2">
								{formatCurrency(annualTotal * 12)}<span class="text-lg font-normal text-muted-foreground">/yr</span>
							</div>
							<div class="text-sm text-muted-foreground font-mono mb-4">
								{formatCurrency(annualTotal)}/month
							</div>
							{#if savingsVsMonthly > 0}
								<div class="flex items-center gap-2 text-sm text-datadog-green">
									<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M12 5v14M5 12l7 7 7-7" />
									</svg>
									Save {formatCurrency(savingsVsMonthly * 12)}/yr ({savingsPercentVsMonthly}%) vs monthly
								</div>
							{/if}
							{#if savingsVsOnDemand > 0}
								<div class="flex items-center gap-2 text-sm text-datadog-green mt-1">
									<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M12 5v14M5 12l7 7 7-7" />
									</svg>
									Save {formatCurrency(savingsVsOnDemand * 12)}/yr ({savingsPercentVsOnDemand}%) vs on-demand
								</div>
							{/if}
						</div>
					{:else if selectedTier === 'monthly'}
						<!-- Monthly -->
						<div class="rounded-lg border-2 border-datadog-blue/50 bg-datadog-blue/5 p-6">
							<div class="flex items-center justify-between mb-3">
								<span class="text-lg font-semibold text-datadog-blue">Billed Monthly</span>
							</div>
							<div class="text-4xl font-bold text-datadog-blue font-mono mb-2">
								{formatCurrency(monthlyTotal * 12)}<span class="text-lg font-normal text-muted-foreground">/yr</span>
							</div>
							<div class="text-sm text-muted-foreground font-mono mb-4">
								{formatCurrency(monthlyTotal)}/month
							</div>
							{#if savingsVsMonthly > 0}
								<div class="flex items-center gap-2 text-sm text-muted-foreground">
									<svg class="h-4 w-4 text-datadog-orange" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M12 19V5M5 12l7-7 7 7" />
									</svg>
									+{formatCurrency(savingsVsMonthly * 12)}/yr vs annual billing
								</div>
							{/if}
						</div>
					{:else}
						<!-- On-Demand -->
						<div class="rounded-lg border-2 border-datadog-orange/50 bg-datadog-orange/5 p-6">
							<div class="flex items-center justify-between mb-3">
								<span class="text-lg font-semibold text-datadog-orange">On-Demand</span>
							</div>
							<div class="text-4xl font-bold text-datadog-orange font-mono mb-2">
								{formatCurrency(onDemandTotal * 12)}<span class="text-lg font-normal text-muted-foreground">/yr</span>
							</div>
							<div class="text-sm text-muted-foreground font-mono mb-4">
								{formatCurrency(onDemandTotal)}/month
							</div>
							{#if savingsVsOnDemand > 0}
								<div class="flex items-center gap-2 text-sm text-muted-foreground">
									<svg class="h-4 w-4 text-datadog-orange" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
										<path d="M12 19V5M5 12l7-7 7 7" />
									</svg>
									+{formatCurrency(savingsVsOnDemand * 12)}/yr vs annual billing
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</CardContent>
		</Card>

		<!-- Actions -->
		<div class="flex flex-wrap items-center justify-center gap-3 print:hidden">
			<!-- Billing Selection Dropdown -->
				<!-- svelte-ignore a11y-click-events-have-key-events -->
				<!-- svelte-ignore a11y-no-static-element-interactions -->
				<div class="relative" on:click|stopPropagation>
					<Button 
						variant="outline" 
						on:click={() => tierMenuOpen = !tierMenuOpen}
						class="gap-2"
					>
						<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M3 6h18M7 12h10M10 18h4" />
						</svg>
						{tierLabel}
						<span class="w-2 h-2 rounded-full bg-{tierColor}"></span>
					</Button>
					
					{#if tierMenuOpen}
						<div class="absolute left-0 top-full mt-2 w-48 rounded-xl border border-border bg-card p-2 shadow-2xl z-50">
							<button
								type="button"
								class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-muted"
								on:click={() => { selectedTier = 'annual'; tierMenuOpen = false; }}
							>
								<span class="w-4 h-4 rounded-full border-2 flex items-center justify-center {selectedTier === 'annual' ? 'border-datadog-green' : 'border-muted-foreground/30'}">
									{#if selectedTier === 'annual'}
										<span class="w-2 h-2 rounded-full bg-datadog-green"></span>
									{/if}
								</span>
								<span class="text-datadog-green font-medium">Annually</span>
								{#if savingsVsMonthly > 0 || savingsVsOnDemand > 0}
									<Badge variant="outline" class="ml-auto text-[10px] text-datadog-green border-datadog-green/50">Best</Badge>
								{/if}
							</button>
							<button
								type="button"
								class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-muted"
								on:click={() => { selectedTier = 'monthly'; tierMenuOpen = false; }}
							>
								<span class="w-4 h-4 rounded-full border-2 flex items-center justify-center {selectedTier === 'monthly' ? 'border-datadog-blue' : 'border-muted-foreground/30'}">
									{#if selectedTier === 'monthly'}
										<span class="w-2 h-2 rounded-full bg-datadog-blue"></span>
									{/if}
								</span>
								<span class="text-datadog-blue font-medium">Monthly</span>
							</button>
							<button
								type="button"
								class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-muted"
								on:click={() => { selectedTier = 'on-demand'; tierMenuOpen = false; }}
							>
								<span class="w-4 h-4 rounded-full border-2 flex items-center justify-center {selectedTier === 'on-demand' ? 'border-datadog-orange' : 'border-muted-foreground/30'}">
									{#if selectedTier === 'on-demand'}
										<span class="w-2 h-2 rounded-full bg-datadog-orange"></span>
									{/if}
								</span>
								<span class="text-datadog-orange font-medium">On-Demand</span>
							</button>
						</div>
					{/if}
				</div>
				
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
				<Button variant="outline" on:click={attemptEdit} class="gap-2">
					{#if quote.is_protected && !isUnlocked}
						<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
							<path d="M7 11V7a5 5 0 0110 0v4" />
						</svg>
					{:else}
						<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
							<path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
						</svg>
					{/if}
					Edit
				</Button>
				<Button on:click={cloneQuote} class="gap-2 bg-datadog-purple hover:bg-datadog-purple/90">
					<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<rect x="9" y="9" width="13" height="13" rx="2" />
						<path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
					</svg>
					Clone
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

<!-- Password Modal -->
{#if passwordModalOpen}
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div 
		class="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm"
		on:click|self={() => passwordModalOpen = false}
		on:keydown={(e) => e.key === 'Escape' && (passwordModalOpen = false)}
		role="dialog"
		aria-modal="true"
		tabindex="-1"
	>
		<div class="relative w-full max-w-sm rounded-2xl border border-border bg-card p-6 shadow-2xl">
			<!-- Close Button -->
			<button
				type="button"
				class="absolute right-4 top-4 rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
				on:click={() => passwordModalOpen = false}
			>
				<svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M18 6L6 18M6 6l12 12" />
				</svg>
			</button>

			<div class="flex items-center gap-3 mb-6">
				<div class="flex h-11 w-11 items-center justify-center rounded-xl bg-datadog-purple shadow-lg shadow-datadog-purple/30">
					<svg class="h-6 w-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
						<path d="M7 11V7a5 5 0 0110 0v4" />
					</svg>
				</div>
				<div>
					<h2 class="text-xl font-semibold">Password Required</h2>
					<p class="text-sm text-muted-foreground">Enter password to edit this quote</p>
				</div>
			</div>

			<form on:submit|preventDefault={verifyAndUnlock}>
				<div class="mb-4">
					<label for="edit-password" class="mb-2 block text-sm font-medium">Password</label>
					<Input 
						id="edit-password"
						type="password"
						bind:value={editPassword} 
						placeholder="Enter edit password"
						autofocus
					/>
				</div>
				
				{#if passwordError}
					<p class="mb-4 text-sm text-destructive">{passwordError}</p>
				{/if}

				<div class="flex gap-3">
					<Button 
						type="button"
						variant="outline" 
						class="flex-1"
						on:click={() => passwordModalOpen = false}
					>
						Cancel
					</Button>
					<Button 
						type="submit"
						class="flex-1 bg-datadog-purple hover:bg-datadog-purple/90"
						disabled={verifying || !editPassword}
					>
						{#if verifying}
							<svg class="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M21 12a9 9 0 11-6.219-8.56" />
							</svg>
							Verifying...
						{:else}
							Unlock
						{/if}
					</Button>
				</div>
			</form>
		</div>
	</div>
{/if}

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

