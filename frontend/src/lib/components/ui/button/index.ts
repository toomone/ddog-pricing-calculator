import { tv, type VariantProps } from 'tailwind-variants';
import Root from './Button.svelte';

const buttonVariants = tv({
	base: 'inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]',
	variants: {
		variant: {
			default: 'bg-datadog-purple text-white hover:bg-datadog-violet shadow-lg shadow-datadog-purple/25',
			destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
			outline: 'border border-input bg-background text-foreground hover:bg-accent hover:text-accent-foreground',
			secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
			ghost: 'hover:bg-accent hover:text-accent-foreground',
			link: 'text-primary underline-offset-4 hover:underline',
			success: 'bg-datadog-green text-white hover:bg-datadog-green/90 shadow-lg shadow-datadog-green/25'
		},
		size: {
			default: 'h-10 px-4 py-2',
			sm: 'h-9 rounded-md px-3',
			lg: 'h-12 rounded-xl px-8 text-base',
			icon: 'h-10 w-10'
		}
	},
	defaultVariants: {
		variant: 'default',
		size: 'default'
	}
});

type Variant = VariantProps<typeof buttonVariants>['variant'];
type Size = VariantProps<typeof buttonVariants>['size'];

export {
	Root,
	Root as Button,
	buttonVariants,
	type Variant,
	type Size
};

