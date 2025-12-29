<script lang="ts">
	import { slide, fade } from 'svelte/transition';
	import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Badge } from '$lib/components/ui/badge';
	import * as Tabs from '$lib/components/ui/tabs';
	import { formatCurrency, formatNumber } from '$lib/utils';
	import type { Product } from '$lib/api';

	export let products: Product[] = [];
	export let onAddToQuote: (items: { product: Product; quantity: number }[]) => void = () => {};

	// Wizard state
	let currentStep = 'volume';
	let showAdvancedOptions = false;

	// User inputs
	let ingestedLogsGB = 100;
	let avgLogSizeKB = 2;
	let indexingPercentage = 15;
	let retentionDays: 3 | 7 | 15 | 30 = 15;

	// Additional options
	let enableFlexStarter = false;
	let enableFlexStorage = false;
	let enableForwarding = false;
	let flexStarterEvents = 10;
	let flexStorageEvents = 50;
	let forwardingGB = 20;

	// Presets
	const useCasePresets = [
		{ name: 'Minimal', percentage: 5, description: 'Errors only' },
		{ name: 'Standard', percentage: 15, description: 'Debug + Errors' },
		{ name: 'Extended', percentage: 30, description: 'Most logs' },
		{ name: 'Full', percentage: 100, description: 'Everything' },
	];

	const retentionOptions = [
		{ days: 3 as const, label: '3 days', description: 'Quick debugging' },
		{ days: 7 as const, label: '7 days', description: 'Weekly review' },
		{ days: 15 as const, label: '15 days', description: 'Standard' },
		{ days: 30 as const, label: '30 days', description: 'Extended' },
	];

	// Calculations
	$: totalLogsPerMonth = (ingestedLogsGB * 1024 * 1024) / avgLogSizeKB;
	$: indexedLogsCount = totalLogsPerMonth * (indexingPercentage / 100);
	$: indexedLogsInMillions = indexedLogsCount / 1_000_000;

	// Products lookup
	$: ingestionProduct = products.find(p => 
		p.product.toLowerCase().includes('logs') && 
		p.product.toLowerCase().includes('ingestion')
	);
	$: indexedProduct = products.find(p => 
		p.product.toLowerCase().includes('indexed log events') &&
		p.billing_unit.toLowerCase().includes(`${retentionDays}-day`)
	);
	$: flexStarterProduct = products.find(p => p.product === 'Flex Logs Starter');
	$: flexStorageProduct = products.find(p => p.product === 'Flex Logs Storage');
	$: forwardingProduct = products.find(p => p.product === 'Logs - Forwarding to Custom Destinations');

	function parsePrice(priceStr: string | null): number {
		if (!priceStr) return 0;
		const match = priceStr.match(/[\d.]+/);
		return match ? parseFloat(match[0]) : 0;
	}

	$: ingestionPrice = parsePrice(ingestionProduct?.billed_annually);
	$: indexedPrice = parsePrice(indexedProduct?.billed_annually);
	$: flexStarterPrice = parsePrice(flexStarterProduct?.billed_annually);
	$: flexStoragePrice = parsePrice(flexStorageProduct?.billed_annually);
	$: forwardingPrice = parsePrice(forwardingProduct?.billed_annually);

	$: ingestionCost = ingestedLogsGB * ingestionPrice;
	$: indexedCost = indexedLogsInMillions * indexedPrice;
	$: flexStarterCost = enableFlexStarter ? flexStarterEvents * flexStarterPrice : 0;
	$: flexStorageCost = enableFlexStorage ? flexStorageEvents * flexStoragePrice : 0;
	$: forwardingCost = enableForwarding ? forwardingGB * forwardingPrice : 0;
	$: additionalCost = flexStarterCost + flexStorageCost + forwardingCost;
	$: totalMonthlyCost = ingestionCost + indexedCost + additionalCost;

	function addToQuote() {
		const items: { product: Product; quantity: number }[] = [];
		if (ingestionProduct && ingestedLogsGB > 0) {
			items.push({ product: ingestionProduct, quantity: Math.ceil(ingestedLogsGB) });
		}
		if (indexedProduct && indexedLogsInMillions > 0) {
			items.push({ product: indexedProduct, quantity: Math.ceil(indexedLogsInMillions) });
		}
		if (enableFlexStarter && flexStarterProduct && flexStarterEvents > 0) {
			items.push({ product: flexStarterProduct, quantity: Math.ceil(flexStarterEvents) });
		}
		if (enableFlexStorage && flexStorageProduct && flexStorageEvents > 0) {
			items.push({ product: flexStorageProduct, quantity: Math.ceil(flexStorageEvents) });
		}
		if (enableForwarding && forwardingProduct && forwardingGB > 0) {
			items.push({ product: forwardingProduct, quantity: Math.ceil(forwardingGB) });
		}
		if (items.length > 0) onAddToQuote(items);
	}
</script>

<Card class="border-datadog-purple/20 overflow-hidden">
	<CardContent class="p-0">
		<!-- ROW 1: Title -->
		<div class="px-6 py-4 border-b border-border">
			<h2 class="text-lg font-semibold">Log Indexing Estimator</h2>
			<p class="text-sm text-muted-foreground">Estimate your log indexing needs based on ingestion volume</p>
		</div>

		<!-- ROW 2: Summary -->
		<div class="flex items-center justify-between px-6 py-3 border-b border-border">
			<!-- Left: Selected quantities -->
			<div class="flex items-center gap-4 text-[13px] text-muted-foreground">
				<span class="font-medium">Selected:</span>
				<span><span class="font-mono font-medium text-foreground">{ingestedLogsGB}</span> GB</span>
				<span>·</span>
				<span><span class="font-mono font-medium text-foreground">{retentionDays}</span> days</span>
				<span>·</span>
				<span><span class="font-mono font-medium text-foreground">{indexingPercentage}%</span> indexed</span>
				<span>·</span>
				<span><span class="font-mono font-medium text-foreground">{indexedLogsInMillions.toFixed(1)}M</span> logs</span>
				{#if enableFlexStarter || enableFlexStorage || enableForwarding}
					<span>·</span>
					<span class="text-datadog-blue font-medium">+ extras</span>
				{/if}
			</div>

			<!-- Right: Total -->
			<div class="text-right">
				<div class="text-2xl font-bold font-mono text-datadog-green">
					{formatCurrency(totalMonthlyCost)}
				</div>
				<div class="text-xs text-muted-foreground">per month</div>
			</div>
		</div>

		<!-- ROW 3: Tabs -->
		<div class="px-6 py-3 border-b border-border bg-muted/30">
			<Tabs.Root bind:value={currentStep}>
				<Tabs.List class="w-full grid grid-cols-4">
					<Tabs.Trigger value="volume">Volume</Tabs.Trigger>
					<Tabs.Trigger value="retention">Retention</Tabs.Trigger>
					<Tabs.Trigger value="indexing">Indexing</Tabs.Trigger>
					<Tabs.Trigger value="extras">Extras</Tabs.Trigger>
				</Tabs.List>
			</Tabs.Root>
		</div>

		<!-- ROW 4: Form Content -->
		<div class="grid grid-cols-[1fr_1px_2fr_1px_1fr] min-h-[300px]">
			
			<!-- Left Panel: Info -->
			<div class="p-6 flex flex-col justify-center">
				{#if currentStep === 'volume'}
					<h3 class="text-lg font-semibold mb-2">Log Volume</h3>
					<p class="text-xs text-muted-foreground">
						Enter your monthly log ingestion volume and average log size to calculate the number of log events.
					</p>
					<div class="mt-4 p-3 bg-datadog-blue/5 border-l-2 border-datadog-blue">
						<div class="text-xs text-muted-foreground">Calculated logs</div>
						<div class="text-xl font-bold font-mono">{formatNumber(Math.round(totalLogsPerMonth))}</div>
						<div class="text-xs text-muted-foreground">events/month</div>
					</div>
				{:else if currentStep === 'retention'}
					<h3 class="text-lg font-semibold mb-2">Retention Period</h3>
					<p class="text-xs text-muted-foreground">
						Choose how long indexed logs should remain searchable. Longer retention costs more per event.
					</p>
				{:else if currentStep === 'indexing'}
					<h3 class="text-lg font-semibold mb-2">Indexing Strategy</h3>
					<p class="text-xs text-muted-foreground">
						Select what percentage of logs to index for search. Index only what you need to query.
					</p>
					<div class="mt-4 p-3 bg-datadog-purple/5 border-l-2 border-datadog-purple">
						<div class="text-xs text-muted-foreground">Indexed logs</div>
						<div class="text-xl font-bold font-mono text-datadog-purple">{formatNumber(Math.round(indexedLogsCount))}</div>
						<div class="text-xs text-muted-foreground">{indexedLogsInMillions.toFixed(2)}M events</div>
					</div>
				{:else if currentStep === 'extras'}
					<h3 class="text-lg font-semibold mb-2">Additional Options</h3>
					<p class="text-xs text-muted-foreground">
						Optional features for advanced use cases. Skip if not needed.
					</p>
				{/if}
			</div>

			<!-- Separator -->
			<div class="bg-border"></div>

			<!-- Center Panel: Form -->
			<div class="p-6">
				{#if currentStep === 'volume'}
					<div class="space-y-6">
						<div class="space-y-2">
							<label for="ingestedLogs" class="text-sm font-medium">
								Monthly ingestion volume (GB)
							</label>
							<Input 
								id="ingestedLogs"
								type="number" 
								bind:value={ingestedLogsGB} 
								min="1" 
								class="font-mono text-lg max-w-xs"
							/>
						</div>

						<!-- Advanced Options (Collapsible) -->
						<div class="border-t border-border pt-4">
							<button
								type="button"
								class="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
								on:click={() => showAdvancedOptions = !showAdvancedOptions}
							>
								<svg 
									class="w-4 h-4 transition-transform {showAdvancedOptions ? 'rotate-90' : ''}" 
									viewBox="0 0 24 24" 
									fill="none" 
									stroke="currentColor" 
									stroke-width="2"
								>
									<path d="M9 18l6-6-6-6"/>
								</svg>
								Advanced options
							</button>
							
							{#if showAdvancedOptions}
								<div class="mt-4 space-y-2" transition:slide={{ duration: 150 }}>
									<label for="avgLogSize" class="text-sm font-medium">
										Average log entry size (KB)
									</label>
									<Input 
										id="avgLogSize"
										type="number" 
										bind:value={avgLogSizeKB} 
										min="0.1" 
										step="0.1"
										class="font-mono max-w-xs"
									/>
									<p class="text-xs text-muted-foreground">
										Typical: JSON ~1-2KB, plain text ~0.5KB
									</p>
								</div>
							{/if}
						</div>
					</div>

				{:else if currentStep === 'retention'}
					<div class="grid grid-cols-2 gap-3">
						{#each retentionOptions as option}
							<button
								type="button"
								class="p-4 border text-left transition-all
									{retentionDays === option.days 
										? 'border-datadog-purple bg-datadog-purple/10' 
										: 'border-border hover:border-datadog-purple/50 hover:bg-muted/50'}"
								on:click={() => retentionDays = option.days}
							>
								<div class="font-bold text-lg">{option.label}</div>
								<div class="text-sm text-muted-foreground">{option.description}</div>
							</button>
						{/each}
					</div>

				{:else if currentStep === 'indexing'}
					<div class="space-y-6">
						<div class="grid grid-cols-2 gap-3">
							{#each useCasePresets as preset}
								<button
									type="button"
									class="p-4 border text-left transition-all
										{indexingPercentage === preset.percentage 
											? 'border-datadog-green bg-datadog-green/10' 
											: 'border-border hover:border-datadog-green/50'}"
									on:click={() => indexingPercentage = preset.percentage}
								>
									<div class="flex items-center justify-between">
										<span class="font-bold">{preset.name}</span>
										<Badge variant="outline">{preset.percentage}%</Badge>
									</div>
									<div class="text-sm text-muted-foreground">{preset.description}</div>
								</button>
							{/each}
						</div>
						<div class="space-y-2">
							<div class="flex justify-between text-sm">
								<span>Custom percentage</span>
								<span class="font-mono font-bold text-datadog-purple">{indexingPercentage}%</span>
							</div>
							<input 
								type="range" 
								bind:value={indexingPercentage} 
								min="1" 
								max="100" 
								class="w-full accent-datadog-purple h-2"
							/>
						</div>
					</div>

				{:else if currentStep === 'extras'}
					<div class="space-y-3">
						<label
							class="flex items-start gap-3 p-4 border cursor-pointer transition-all
								{enableFlexStarter ? 'border-datadog-blue bg-datadog-blue/5' : 'border-border hover:border-muted-foreground'}"
						>
							<input 
								type="checkbox" 
								bind:checked={enableFlexStarter}
								class="mt-0.5 h-4 w-4 accent-datadog-blue"
							/>
							<div class="flex-1">
								<div class="font-medium text-sm">Flex Logs Starter</div>
								<div class="text-xs text-muted-foreground">Query archived logs cost-effectively</div>
								{#if enableFlexStarter}
									<div class="mt-2 flex items-center gap-2" transition:slide={{ duration: 150 }}>
										<Input type="number" bind:value={flexStarterEvents} min="1" class="w-20 font-mono text-sm" />
										<span class="text-xs text-muted-foreground">M events</span>
										{#if flexStarterPrice > 0}
											<span class="text-xs text-datadog-blue ml-auto">{formatCurrency(flexStarterCost)}/mo</span>
										{/if}
									</div>
								{/if}
							</div>
						</label>

						<label
							class="flex items-start gap-3 p-4 border cursor-pointer transition-all
								{enableFlexStorage ? 'border-datadog-blue bg-datadog-blue/5' : 'border-border hover:border-muted-foreground'}"
						>
							<input 
								type="checkbox" 
								bind:checked={enableFlexStorage}
								class="mt-0.5 h-4 w-4 accent-datadog-blue"
							/>
							<div class="flex-1">
								<div class="font-medium text-sm">Flex Logs Storage</div>
								<div class="text-xs text-muted-foreground">Long-term storage for compliance</div>
								{#if enableFlexStorage}
									<div class="mt-2 flex items-center gap-2" transition:slide={{ duration: 150 }}>
										<Input type="number" bind:value={flexStorageEvents} min="1" class="w-20 font-mono text-sm" />
										<span class="text-xs text-muted-foreground">M events</span>
										{#if flexStoragePrice > 0}
											<span class="text-xs text-datadog-blue ml-auto">{formatCurrency(flexStorageCost)}/mo</span>
										{/if}
									</div>
								{/if}
							</div>
						</label>

						<label
							class="flex items-start gap-3 p-4 border cursor-pointer transition-all
								{enableForwarding ? 'border-datadog-orange bg-datadog-orange/5' : 'border-border hover:border-muted-foreground'}"
						>
							<input 
								type="checkbox" 
								bind:checked={enableForwarding}
								class="mt-0.5 h-4 w-4 accent-datadog-orange"
							/>
							<div class="flex-1">
								<div class="font-medium text-sm">Log Forwarding</div>
								<div class="text-xs text-muted-foreground">Forward to S3, Azure, GCS</div>
								{#if enableForwarding}
									<div class="mt-2 flex items-center gap-2" transition:slide={{ duration: 150 }}>
										<Input type="number" bind:value={forwardingGB} min="1" class="w-20 font-mono text-sm" />
										<span class="text-xs text-muted-foreground">GB/mo</span>
										{#if forwardingPrice > 0}
											<span class="text-xs text-datadog-orange ml-auto">{formatCurrency(forwardingCost)}/mo</span>
										{/if}
									</div>
								{/if}
							</div>
						</label>
					</div>
				{/if}
			</div>

			<!-- Separator -->
			<div class="bg-border"></div>

			<!-- Right Panel: Cost Breakdown -->
			<div class="p-6">
				<h4 class="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-4">Cost Breakdown</h4>
				<div class="space-y-3 text-sm">
					<div>
						<div class="flex items-center gap-2">
							<div class="w-2 h-2 bg-datadog-blue"></div>
							<span>Ingestion</span>
						</div>
						<div class="font-mono text-right">{formatCurrency(ingestionCost)}</div>
					</div>
					<div>
						<div class="flex items-center gap-2">
							<div class="w-2 h-2 bg-datadog-purple"></div>
							<span>Indexed ({retentionDays}d)</span>
						</div>
						<div class="font-mono text-right">{formatCurrency(indexedCost)}</div>
					</div>
					{#if enableFlexStarter}
						<div class="flex items-start justify-between text-datadog-blue">
							<span>Flex Starter</span>
							<span class="font-mono text-right">{formatCurrency(flexStarterCost)}</span>
						</div>
					{/if}
					{#if enableFlexStorage}
						<div class="flex items-start justify-between text-datadog-blue">
							<span>Flex Storage</span>
							<span class="font-mono text-right">{formatCurrency(flexStorageCost)}</span>
						</div>
					{/if}
					{#if enableForwarding}
						<div class="flex items-start justify-between text-datadog-orange">
							<span>Forwarding</span>
							<span class="font-mono text-right">{formatCurrency(forwardingCost)}</span>
						</div>
					{/if}
				</div>

				<!-- Visual bar -->
				{#if totalMonthlyCost > 0}
					<div class="mt-4">
						<div class="h-2 flex overflow-hidden">
							<div class="bg-datadog-blue" style="width: {(ingestionCost / totalMonthlyCost) * 100}%"></div>
							<div class="bg-datadog-purple" style="width: {(indexedCost / totalMonthlyCost) * 100}%"></div>
							{#if additionalCost > 0}
								<div class="bg-datadog-green" style="width: {(additionalCost / totalMonthlyCost) * 100}%"></div>
							{/if}
						</div>
					</div>
				{/if}

				<div class="mt-4 pt-4 border-t border-border">
					<div class="flex justify-between items-center text-muted-foreground text-xs">
						<span>Monthly</span>
						<span class="font-mono">{formatCurrency(totalMonthlyCost)}</span>
					</div>
					<div class="flex justify-between items-center mt-2">
						<span class="font-medium">Annual</span>
						<span class="font-mono font-bold text-lg text-datadog-green">{formatCurrency(totalMonthlyCost * 12)}</span>
					</div>
				</div>
			</div>
		</div>

		<!-- ROW 5: Action Button -->
		<div class="flex items-center justify-end px-6 py-4 border-t border-border">
			<Button 
				class="bg-datadog-purple hover:bg-datadog-purple/90"
				on:click={addToQuote}
				disabled={!ingestionProduct || !indexedProduct}
			>
				Add to Quote
			</Button>
		</div>

		{#if !ingestionProduct || !indexedProduct}
			<div class="px-6 py-2 bg-amber-50 border-t border-amber-200 text-xs text-amber-700 text-center">
				⚠️ Some log products not found. Please sync pricing data.
			</div>
		{/if}
	</CardContent>
</Card>
