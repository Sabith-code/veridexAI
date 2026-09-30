import ChatWindow from '@/components/ChatWindow';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Chat - Veridex',
  description: 'Chat with the internet, chat with Veridex.',
};

const Home = () => {
  return <ChatWindow />;
};

export default Home;
