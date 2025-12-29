<script lang="ts">
	import { slide, fade } from 'svelte/transition';
	import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Badge } from '$lib/components/ui/badge';
	import { formatCurrency, formatNumber } from '$lib/utils';
	import type { Product } from '$lib/api';

	export let products: Product[] = [];
	export let onAddToQuote: (items: { product: Product; quantity: number }[]) => void = () => {};

	// Wizard state
	let currentStep = 0;
	const steps = [
		{ id: 'volume', title: 'Volume', icon: '📊', description: 'How much data?' },
		{ id: 'retention', title: 'Retention', icon: '📅', description: 'How long?' },
		{ id: 'indexing', title: 'Indexing', icon: '🔍', description: 'What to search?' },
		{ id: 'extras', title: 'Extras', icon: '⚡', description: 'Options' },
	];

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
		{ name: 'Minimal', percentage: 5, emoji: '🎯', description: 'Errors only' },
		{ name: 'Standard', percentage: 15, emoji: '⚖️', description: 'Debug + Errors' },
		{ name: 'Extended', percentage: 30, emoji: '🔬', description: 'Most logs' },
		{ name: 'Full', percentage: 100, emoji: '📦', description: 'Everything' },
	];

	const retentionOptions = [
		{ days: 3 as const, label: '3 days', emoji: '⚡', description: 'Quick debugging' },
		{ days: 7 as const, label: '7 days', emoji: '📆', description: 'Weekly review' },
		{ days: 15 as const, label: '15 days', emoji: '📊', description: 'Standard' },
		{ days: 30 as const, label: '30 days', emoji: '🗄️', description: 'Extended' },
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

	// Navigation
	function goToStep(index: number) {
		currentStep = index;
	}

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
	<CardHeader class="bg-gradient-to-r from-datadog-purple/10 to-datadog-blue/10 pb-4">
		<div class="flex items-center gap-3">
			<div class="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-datadog-purple to-datadog-blue text-xl">
				📋
			</div>
			<div>
				<CardTitle>Log Indexing Wizard</CardTitle>
				<CardDescription>Configure your log indexing step by step</CardDescription>
			</div>
		</div>
	</CardHeader>

	<CardContent class="space-y-6 pt-6">
		
		<!-- ROW 1: Cost Summary -->
		<div class="rounded-xl border border-border bg-gradient-to-r from-muted/50 to-muted/30 p-4">
			<div class="flex flex-col lg:flex-row lg:items-center gap-4">
				
				<!-- Stats -->
				<div class="flex flex-wrap items-center gap-x-6 gap-y-2 flex-1">
					<div class="flex items-center gap-2">
						<span class="text-xs text-muted-foreground">Volume:</span>
						<span class="font-mono font-medium">{ingestedLogsGB} GB</span>
					</div>
					<div class="flex items-center gap-2">
						<span class="text-xs text-muted-foreground">Retention:</span>
						<span class="font-mono font-medium">{retentionDays}d</span>
					</div>
					<div class="flex items-center gap-2">
						<span class="text-xs text-muted-foreground">Indexing:</span>
						<span class="font-mono font-medium">{indexingPercentage}%</span>
					</div>
					<div class="flex items-center gap-2">
						<span class="text-xs text-muted-foreground">Indexed:</span>
						<span class="font-mono text-sm">{indexedLogsInMillions.toFixed(1)}M logs</span>
					</div>
				</div>

				<!-- Cost Breakdown -->
				<div class="flex items-center gap-4">
					<div class="flex items-center gap-3 text-sm">
						<div class="flex items-center gap-1.5">
							<div class="w-2 h-2 rounded bg-datadog-blue"></div>
							<span class="font-mono">{formatCurrency(ingestionCost)}</span>
						</div>
						<span class="text-muted-foreground">+</span>
						<div class="flex items-center gap-1.5">
							<div class="w-2 h-2 rounded bg-datadog-purple"></div>
							<span class="font-mono">{formatCurrency(indexedCost)}</span>
						</div>
						{#if additionalCost > 0}
							<span class="text-muted-foreground">+</span>
							<div class="flex items-center gap-1.5">
								<div class="w-2 h-2 rounded bg-datadog-green"></div>
								<span class="font-mono">{formatCurrency(additionalCost)}</span>
							</div>
						{/if}
					</div>
					
					<div class="text-muted-foreground">=</div>
					
					<!-- Total -->
					<div class="rounded-lg bg-datadog-green/10 border border-datadog-green/30 px-4 py-2 text-center">
						<div class="text-xl font-bold font-mono text-datadog-green">
							{formatCurrency(totalMonthlyCost)}
						</div>
						<div class="text-[10px] text-muted-foreground">/month</div>
					</div>
					
					<!-- Add to Quote Button -->
					<Button 
						class="bg-datadog-purple hover:bg-datadog-purple/90 gap-2"
						on:click={addToQuote}
						disabled={!ingestionProduct || !indexedProduct}
					>
						<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M12 5v14M5 12h14"/>
						</svg>
						Add to Quote
					</Button>
				</div>
			</div>
			
			<!-- Cost Visualization Bar -->
			{#if totalMonthlyCost > 0}
				<div class="h-2 rounded-full overflow-hidden bg-muted flex mt-3">
					<div 
						class="bg-datadog-blue transition-all duration-300" 
						style="width: {(ingestionCost / totalMonthlyCost) * 100}%"
						title="Ingestion"
					></div>
					<div 
						class="bg-datadog-purple transition-all duration-300" 
						style="width: {(indexedCost / totalMonthlyCost) * 100}%"
						title="Indexed"
					></div>
					{#if additionalCost > 0}
						<div 
							class="bg-datadog-green transition-all duration-300" 
							style="width: {(additionalCost / totalMonthlyCost) * 100}%"
							title="Extras"
						></div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- ROW 2: Step Buttons -->
		<div class="flex gap-2">
			{#each steps as step, i}
				<button
					type="button"
					class="flex-1 flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-all
						{currentStep === i 
							? 'border-datadog-purple bg-datadog-purple text-white shadow-lg' 
							: currentStep > i
								? 'border-datadog-green/50 bg-datadog-green/10 text-datadog-green hover:bg-datadog-green/20'
								: 'border-border hover:border-muted-foreground hover:bg-muted/50'}"
					on:click={() => goToStep(i)}
				>
					<span class="text-lg">{currentStep > i ? '✓' : step.icon}</span>
					<div class="text-left hidden sm:block">
						<div class="font-medium text-sm leading-tight">{step.title}</div>
						<div class="text-[10px] opacity-70">{step.description}</div>
					</div>
					<span class="sm:hidden font-medium text-sm">{step.title}</span>
				</button>
			{/each}
		</div>

		<!-- ROW 3: Form Content -->
		<div class="min-h-[320px] rounded-xl border border-border bg-muted/20 p-6">
			{#key currentStep}
				<div in:fade={{ duration: 150 }}>
					
					<!-- Step 0: Volume -->
					{#if currentStep === 0}
						<div class="space-y-6">
							<div>
								<h3 class="text-lg font-semibold mb-1 flex items-center gap-2">
									<span>📊</span> Log Volume
								</h3>
								<p class="text-sm text-muted-foreground">Tell us about your log ingestion</p>
							</div>

							<div class="grid sm:grid-cols-2 gap-6">
								<div class="space-y-2">
									<label for="ingestedLogs" class="text-sm font-medium">
										Monthly ingestion volume
									</label>
									<div class="flex items-center gap-3">
										<Input 
											id="ingestedLogs"
											type="number" 
											bind:value={ingestedLogsGB} 
											min="1" 
											class="font-mono text-lg w-32"
										/>
										<span class="text-muted-foreground">GB / month</span>
									</div>
								</div>

								<div class="space-y-2">
									<label for="avgLogSize" class="text-sm font-medium">
										Average log entry size
									</label>
									<div class="flex items-center gap-3">
										<Input 
											id="avgLogSize"
											type="number" 
											bind:value={avgLogSizeKB} 
											min="0.1" 
											step="0.1"
											class="font-mono text-lg w-32"
										/>
										<span class="text-muted-foreground">KB per log</span>
									</div>
									<p class="text-xs text-muted-foreground">
										Typical: JSON ~1-2KB, text ~0.5KB
									</p>
								</div>
							</div>

							<div class="rounded-lg bg-datadog-blue/5 border border-datadog-blue/20 p-4 inline-block">
								<div class="text-sm text-muted-foreground">📈 That's approximately</div>
								<div class="text-2xl font-bold font-mono">
									{formatNumber(Math.round(totalLogsPerMonth))} <span class="text-base font-normal text-muted-foreground">log entries/month</span>
								</div>
							</div>
						</div>

					<!-- Step 1: Retention -->
					{:else if currentStep === 1}
						<div class="space-y-6">
							<div>
								<h3 class="text-lg font-semibold mb-1 flex items-center gap-2">
									<span>📅</span> Retention Period
								</h3>
								<p class="text-sm text-muted-foreground">How long should indexed logs be searchable?</p>
							</div>

							<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
								{#each retentionOptions as option}
									<button
										type="button"
										class="p-4 rounded-xl border-2 text-center transition-all
											{retentionDays === option.days 
												? 'border-datadog-purple bg-datadog-purple/10 ring-2 ring-datadog-purple/50' 
												: 'border-border hover:border-datadog-purple/50 hover:bg-muted/50'}"
										on:click={() => retentionDays = option.days}
									>
										<div class="text-2xl mb-1">{option.emoji}</div>
										<div class="font-bold">{option.label}</div>
										<div class="text-xs text-muted-foreground">{option.description}</div>
									</button>
								{/each}
							</div>

							<div class="text-sm text-muted-foreground flex items-center gap-2">
								<span>💡</span>
								<span>Longer retention = higher cost per indexed log</span>
							</div>
						</div>

					<!-- Step 2: Indexing -->
					{:else if currentStep === 2}
						<div class="space-y-6">
							<div>
								<h3 class="text-lg font-semibold mb-1 flex items-center gap-2">
									<span>🔍</span> Indexing Strategy
								</h3>
								<p class="text-sm text-muted-foreground">What percentage of logs do you need to search?</p>
							</div>

							<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
								{#each useCasePresets as preset}
									<button
										type="button"
										class="p-4 rounded-xl border-2 text-center transition-all
											{indexingPercentage === preset.percentage 
												? 'border-datadog-green bg-datadog-green/10' 
												: 'border-border hover:border-datadog-green/50'}"
										on:click={() => indexingPercentage = preset.percentage}
									>
										<div class="text-2xl mb-1">{preset.emoji}</div>
										<div class="font-bold">{preset.name}</div>
										<Badge variant="outline" class="mt-1">{preset.percentage}%</Badge>
										<div class="text-xs text-muted-foreground mt-1">{preset.description}</div>
									</button>
								{/each}
							</div>

							<div class="space-y-2 max-w-md">
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

							<div class="rounded-lg bg-datadog-purple/5 border border-datadog-purple/20 p-4 inline-block">
								<div class="text-sm text-muted-foreground">You'll index</div>
								<div class="text-2xl font-bold font-mono text-datadog-purple">
									{formatNumber(Math.round(indexedLogsCount))} <span class="text-base font-normal">logs ({indexedLogsInMillions.toFixed(2)}M)</span>
								</div>
							</div>
						</div>

					<!-- Step 3: Extras -->
					{:else if currentStep === 3}
						<div class="space-y-5">
							<div>
								<h3 class="text-lg font-semibold mb-1 flex items-center gap-2">
									<span>⚡</span> Additional Options
								</h3>
								<p class="text-sm text-muted-foreground">Optional features — skip if not needed</p>
							</div>

							<div class="grid sm:grid-cols-3 gap-3">
								<!-- Flex Starter -->
								<label
									class="flex flex-col p-4 rounded-xl border-2 cursor-pointer transition-all
										{enableFlexStarter ? 'border-datadog-blue bg-datadog-blue/5' : 'border-border hover:border-muted-foreground'}"
								>
									<div class="flex items-start gap-3">
										<input 
											type="checkbox" 
											bind:checked={enableFlexStarter}
											class="mt-0.5 h-4 w-4 rounded accent-datadog-blue"
										/>
										<div class="flex-1">
											<div class="font-medium text-sm">Flex Logs Starter</div>
											<div class="text-xs text-muted-foreground">Query archived logs</div>
										</div>
									</div>
									{#if enableFlexStarter}
										<div class="mt-3 flex items-center gap-2" transition:slide={{ duration: 150 }}>
											<Input 
												type="number" 
												bind:value={flexStarterEvents} 
												min="1" 
												class="w-20 font-mono text-sm"
											/>
											<span class="text-xs text-muted-foreground">M events</span>
											{#if flexStarterPrice > 0}
												<span class="text-xs text-datadog-blue ml-auto">{formatCurrency(flexStarterCost)}</span>
											{/if}
										</div>
									{/if}
								</label>

								<!-- Flex Storage -->
								<label
									class="flex flex-col p-4 rounded-xl border-2 cursor-pointer transition-all
										{enableFlexStorage ? 'border-datadog-blue bg-datadog-blue/5' : 'border-border hover:border-muted-foreground'}"
								>
									<div class="flex items-start gap-3">
										<input 
											type="checkbox" 
											bind:checked={enableFlexStorage}
											class="mt-0.5 h-4 w-4 rounded accent-datadog-blue"
										/>
										<div class="flex-1">
											<div class="font-medium text-sm">Flex Logs Storage</div>
											<div class="text-xs text-muted-foreground">Long-term compliance</div>
										</div>
									</div>
									{#if enableFlexStorage}
										<div class="mt-3 flex items-center gap-2" transition:slide={{ duration: 150 }}>
											<Input 
												type="number" 
												bind:value={flexStorageEvents} 
												min="1" 
												class="w-20 font-mono text-sm"
											/>
											<span class="text-xs text-muted-foreground">M events</span>
											{#if flexStoragePrice > 0}
												<span class="text-xs text-datadog-blue ml-auto">{formatCurrency(flexStorageCost)}</span>
											{/if}
										</div>
									{/if}
								</label>

								<!-- Forwarding -->
								<label
									class="flex flex-col p-4 rounded-xl border-2 cursor-pointer transition-all
										{enableForwarding ? 'border-datadog-orange bg-datadog-orange/5' : 'border-border hover:border-muted-foreground'}"
								>
									<div class="flex items-start gap-3">
										<input 
											type="checkbox" 
											bind:checked={enableForwarding}
											class="mt-0.5 h-4 w-4 rounded accent-datadog-orange"
										/>
										<div class="flex-1">
											<div class="font-medium text-sm">Log Forwarding</div>
											<div class="text-xs text-muted-foreground">To S3, Azure, GCS</div>
										</div>
									</div>
									{#if enableForwarding}
										<div class="mt-3 flex items-center gap-2" transition:slide={{ duration: 150 }}>
											<Input 
												type="number" 
												bind:value={forwardingGB} 
												min="1" 
												class="w-20 font-mono text-sm"
											/>
											<span class="text-xs text-muted-foreground">GB/mo</span>
											{#if forwardingPrice > 0}
												<span class="text-xs text-datadog-orange ml-auto">{formatCurrency(forwardingCost)}</span>
											{/if}
										</div>
									{/if}
								</label>
							</div>
						</div>
					{/if}
				</div>
			{/key}
		</div>

		{#if !ingestionProduct || !indexedProduct}
			<p class="text-xs text-center text-amber-600 bg-amber-50 rounded-lg p-2">
				⚠️ Some log products not found in pricing data. Please sync pricing first.
			</p>
		{/if}
	</CardContent>
</Card>
